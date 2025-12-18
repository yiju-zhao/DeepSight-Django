import logging
from typing import Literal, cast

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from .config import RAGAgentConfig
from .prompts import (
    SYSTEM_PROMPT,
    format_synthesis_prompt,
    format_grade_documents_prompt,
    format_rewrite_question_prompt,
    HALLUCINATION_GRADER_PROMPT,
    ANSWER_GRADER_PROMPT,
    MAX_RETRIEVAL_ATTEMPTS,
)
from .states import RAGAgentState
from .tools import create_mcp_retrieval_tools
from .utils import format_tool_content

logger = logging.getLogger(__name__)


# --- Data Models for Structured Output ---

class GradeDocuments(BaseModel):
    """Assess relevance of retrieved documents."""
    binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")

class GradeHallucinations(BaseModel):
    """Assess whether the generation is grounded in the documents."""
    binary_score: str = Field(description="Answer is grounded in the facts, 'yes' or 'no'")

class GradeAnswer(BaseModel):
    """Assess whether the answer addresses the question."""
    binary_score: str = Field(description="Answer addresses the question, 'yes' or 'no'")


class DeepSightRAGAgent:
    """
    RAG Agent implementation matching the requested Self-RAG graph structure.
    """

    def __init__(self, config: RAGAgentConfig):
        self.config = config
        self._initialize_models()
        self._build_workflow()

    def _initialize_models(self):
        """Initialize chat models."""
        self.response_model = init_chat_model(
            model=f"openai:{self.config.model_name}",
            api_key=self.config.api_key,
            temperature=self.config.temperature,
        )

        self.grader_model = init_chat_model(
            model=f"openai:{self.config.model_name}",
            api_key=self.config.api_key,
            temperature=self.config.eval_temperature,
        )

        self.synthesis_model = init_chat_model(
            model=f"openai:{self.config.model_name}",
            api_key=self.config.api_key,
            temperature=self.config.synthesis_temperature,
        )

    def _build_workflow(self):
        """Build the workflow graph with nodes and edges."""
        workflow = StateGraph(RAGAgentState)

        # Define the nodes
        workflow.add_node("initialize_request", self.initialize_request)
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade_documents", self.grade_documents)
        workflow.add_node("generate", self.generate)
        workflow.add_node("transform_query", self.transform_query)

        # Build graph
        workflow.add_edge(START, "initialize_request")
        # If initialization fails (no input), end
        workflow.add_conditional_edges(
            "initialize_request",
            self.check_initialization,
            {
                "retrieve": "retrieve",
                "end": END
            }
        )

        workflow.add_edge("retrieve", "grade_documents")
        
        workflow.add_conditional_edges(
            "grade_documents",
            self.decide_to_generate,
            {
                "transform_query": "transform_query",
                "generate": "generate",
            },
        )
        
        workflow.add_edge("transform_query", "retrieve")
        
        workflow.add_conditional_edges(
            "generate",
            self.grade_generation_v_documents_and_question,
            {
                "not supported": "generate", # Loop back to regenerate (simple retry)
                "useful": END,
                "not useful": "transform_query",
            },
        )

        # Add checkpointer for conversation state management
        memory = MemorySaver()
        self.graph = workflow.compile(checkpointer=memory)
        logger.info("RAG agent graph compiled successfully with Self-RAG structure")

    # --- Nodes ---

    def initialize_request(self, state: RAGAgentState) -> dict:
        """Extract user question from messages."""
        logger.info("---INITIALIZE REQUEST---")
        messages = state.get("messages", [])
        question = state.get("question", "")

        # Find the latest human message
        last_human_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_message = msg
                break
        
        if last_human_message:
            question = last_human_message.content
            logger.info(f"Extracted question: {question}")
            return {"question": question, "documents": [], "current_step": "analyzing"}
        
        # If no question is found, we should not proceed.
        # Returning empty dict might leave 'question' empty if not initialized.
        return {"question": "", "documents": []}

    def check_initialization(self, state: RAGAgentState) -> Literal["retrieve", "end"]:
        """Check if we have a valid question to start retrieval."""
        if state.get("question"):
            return "retrieve"
        logger.info("No question found, ending.")
        return "end"

    async def retrieve(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """Retrieve documents."""
        logger.info("---RETRIEVE---")
        question = state["question"]
        
        # Get tools (dynamic)
        tools = config.get("configurable", {}).get("retrieval_tools", [])
        if not tools:
            tools = await create_mcp_retrieval_tools(
                dataset_ids=self.config.dataset_ids,
                mcp_server_url=self.config.mcp_server_url
            )
        
        # Execute retrieval using the first available tool (assuming 1 retrieval tool for now)
        documents = []
        if tools:
            # We use the model to formulate the query for the tool, or just pass the question?
            # Self-RAG typically passes the question.
            # Here we simulate tool execution manually or use bind_tools.
            # To match the "node" style, we'll invoke the tool directly or use the model to call it.
            
            # Simple approach: Search with the question directly
            # This requires knowing the tool implementation.
            # Since our tools are MCP tools, we can't easily invoke them without the model.
            
            # We'll use the model to decide how to search
            model_with_tools = self.response_model.bind_tools(tools)
            response = await model_with_tools.ainvoke([HumanMessage(content=f"Search for: {question}")], config)
            
            # If tool called, execute it
            if response.tool_calls:
                # We need to execute the tool calls.
                # We can use LangGraph's ToolNode for this, but we are inside a custom node.
                # We'll manually execute for this specific flow.
                tool_node = ToolNode(tools)
                # ToolNode expects a state with 'messages' where the last message has tool_calls
                # We construct a temporary state
                temp_state = {"messages": [response]}
                tool_output = await tool_node.ainvoke(temp_state, config)
                
                # Extract content from ToolMessages
                for msg in tool_output["messages"]:
                    if isinstance(msg, ToolMessage):
                        # Format: "Content: ... Source: ..."
                        content = format_tool_content(msg.content)
                        documents.append(content)

        return {"documents": documents, "question": question, "current_step": "retrieving"}

    async def grade_documents(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """Determines whether the retrieved documents are relevant to the question."""
        logger.info("---CHECK DOCUMENT RELEVANCE---")
        question = state["question"]
        documents = state["documents"]
        
        # Score each doc
        filtered_docs = []
        structured_grader = self.grader_model.with_structured_output(GradeDocuments)
        
        graded_docs_meta = [] # For UI

        for d in documents:
            # Grade
            prompt = format_grade_documents_prompt(question=question, context=d)
            score = await structured_grader.ainvoke([HumanMessage(content=prompt)], config)
            grade = score.binary_score
            
            is_relevant = grade.lower() == "yes"
            graded_docs_meta.append({
                "content": d[:100] + "...",
                "score": 1 if is_relevant else 0,
                "relevant": is_relevant,
                "reason": "Graded by LLM"
            })

            if is_relevant:
                logger.info("---GRADE: DOCUMENT RELEVANT---")
                filtered_docs.append(d)
            else:
                logger.info("---GRADE: DOCUMENT NOT RELEVANT---")
                continue
                
        return {
            "documents": filtered_docs, 
            "question": question, 
            "graded_documents": graded_docs_meta,
            "current_step": "grading"
        }

    async def generate(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """Generate answer."""
        logger.info("---GENERATE---")
        question = state["question"]
        documents = state["documents"]
        
        context = "\n\n".join(documents)
        prompt = format_synthesis_prompt(question=question, context=context)
        
        response = await self.synthesis_model.ainvoke([HumanMessage(content=prompt)], config)
        generation = response.content
        
        return {
            "documents": documents, 
            "question": question, 
            "generation": generation,
            "messages": [AIMessage(content=generation)], # Update chat history
            "current_step": "synthesizing",
            "synthesis_progress": 100
        }

    async def transform_query(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """Transform the query to produce a better question."""
        logger.info("---TRANSFORM QUERY---")
        question = state["question"]
        documents = state["documents"]
        
        prompt = format_rewrite_question_prompt(question)
        response = await self.response_model.ainvoke([HumanMessage(content=prompt)], config)
        better_question = response.content
        
        return {
            "documents": documents, 
            "question": better_question,
            "current_step": "rewriting",
            "agent_reasoning": f"Rewrote query to: {better_question}"
        }

    # --- Edges ---

    def decide_to_generate(self, state: RAGAgentState) -> Literal["transform_query", "generate"]:
        """Determines whether to generate an answer, or re-generate a question."""
        logger.info("---ASSESS GRADED DOCUMENTS---")
        filtered_documents = state["documents"]

        if not filtered_documents:
            # All documents have been filtered check_relevance
            logger.info("---DECISION: ALL DOCUMENTS ARE NOT RELEVANT, TRANSFORM QUERY---")
            return "transform_query"
        else:
            # We have relevant documents, so generate answer
            logger.info("---DECISION: GENERATE---")
            return "generate"

    async def grade_generation_v_documents_and_question(self, state: RAGAgentState, config: RunnableConfig) -> Literal["not supported", "useful", "not useful"]:
        """Determines whether the generation is grounded in the document and answers question."""
        logger.info("---CHECK HALLUCINATIONS---")
        question = state["question"]
        documents = state["documents"]
        generation = state["generation"]
        
        context = "\n\n".join(documents)

        # Check hallucination
        hallucination_grader = self.grader_model.with_structured_output(GradeHallucinations)
        
        # We need a prompt for this
        h_prompt = f"Facts:\n{context}\n\nAnswer:\n{generation}"
        score = await hallucination_grader.ainvoke([
            SystemMessage(content=HALLUCINATION_GRADER_PROMPT),
            HumanMessage(content=h_prompt)
        ], config)
        grade = score.binary_score

        if grade.lower() == "yes":
            logger.info("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
            # Check question-answering
            logger.info("---GRADE GENERATION vs QUESTION---")
            
            answer_grader = self.grader_model.with_structured_output(GradeAnswer)
            a_prompt = f"Question: {question}\n\nAnswer:\n{generation}"
            score = await answer_grader.ainvoke([
                SystemMessage(content=ANSWER_GRADER_PROMPT),
                HumanMessage(content=a_prompt)
            ], config)
            grade = score.binary_score
            
            if grade.lower() == "yes":
                logger.info("---DECISION: GENERATION ADDRESSES QUESTION---")
                return "useful"
            else:
                logger.info("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
                return "not useful"
        else:
            logger.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
            return "not supported"

# Define the graph export for direct usage
# We initialize it with a base configuration as nodes handle dynamic overrides
# via config['configurable'] at runtime.
graph = DeepSightRAGAgent(RAGAgentConfig(
    model_name="gpt-4o-mini",
    dataset_ids=[],
    mcp_server_url="http://localhost:9382/mcp/"
)).graph
