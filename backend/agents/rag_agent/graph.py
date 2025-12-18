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
)
from .states import RAGAgentState
from .tools import create_mcp_retrieval_tools
from .utils import format_tool_content
from .context import current_retrieval_tools

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
        """
        Extract user question from messages. 
        Acts as the bridge between CopilotKit (messages) and Self-RAG (question state).
        """
        logger.info("---INITIALIZE REQUEST---")
        messages = state.get("messages", [])
        
        # Find the latest human message
        last_human_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_message = msg
                break
        
        if last_human_message:
            question = last_human_message.content
            logger.info(f"Extracted question: {question}")
            # Reset state for new turn
            return {
                "question": question, 
                "documents": [], 
                "generation": "",
                "current_step": "analyzing"
            }
        
        # If no question is found, return empty to trigger check_initialization -> end
        return {}

    def check_initialization(self, state: RAGAgentState) -> Literal["retrieve", "end"]:
        """Check if we have a valid question to start retrieval."""
        if state.get("question"):
            return "retrieve"
        logger.info("No question found, ending.")
        return "end"

    async def retrieve(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Retrieve documents by calling MCP retrieval tool directly.
        
        This avoids the circular reference issue that occurs when using bind_tools(),
        which embeds tool schemas (containing Pydantic models with circular refs) 
        in the model response that ag_ui_langgraph tries to serialize.
        
        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, documents, that contains retrieved documents
        """
        logger.info("---RETRIEVE---")
        question = state["question"]
        
        # Get tools from context variable (NOT from config to avoid circular refs)
        tools = current_retrieval_tools.get()
        if not tools:
            # Fallback: create tools from config (for standalone usage)
            tools = await create_mcp_retrieval_tools(
                dataset_ids=self.config.dataset_ids,
                mcp_server_url=self.config.mcp_server_url
            )
        
        documents = []
        if tools:
            # Call the retrieval tool directly instead of bind_tools()
            # This avoids embedding circular-reference tool schemas in the response
            for tool in tools:
                if "retrieval" in tool.name.lower() or "search" in tool.name.lower():
                    try:
                        # Invoke the tool directly with the question
                        result = await tool.ainvoke({"query": question}, config)
                        # Format and add the result
                        content = format_tool_content(result)
                        if content:
                            documents.append(content)
                        logger.info(f"Retrieved {len(documents)} documents")
                        break  # Use the first matching retrieval tool
                    except Exception as e:
                        logger.error(f"Error calling retrieval tool: {e}")
                        # Continue to try other tools or return empty

        return {"documents": documents, "question": question, "current_step": "retrieving"}

    async def grade_documents(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Determines whether the retrieved documents are relevant to the question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with only filtered relevant documents
        """
        logger.info("---CHECK DOCUMENT RELEVANCE---")
        question = state["question"]
        documents = state["documents"]
        
        # Score each doc
        filtered_docs = []
        structured_grader = self.grader_model.with_structured_output(GradeDocuments)
        
        graded_docs_meta = [] # For UI

        for d in documents:
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
        """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        logger.info("---GENERATE---")
        question = state["question"]
        documents = state["documents"]
        
        context = "\n\n".join(documents)
        prompt = format_synthesis_prompt(question=question, context=context)
        
        response = await self.synthesis_model.ainvoke([HumanMessage(content=prompt)], config)
        generation = response.content
        
        # We also append the generation to the chat history for CopilotKit
        return {
            "documents": documents, 
            "question": question, 
            "generation": generation,
            "messages": [AIMessage(content=generation)],
            "current_step": "synthesizing",
            "synthesis_progress": 100
        }

    async def transform_query(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Transform the query to produce a better question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates question key with a re-phrased question
        """
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
        """
        Determines whether to generate an answer, or re-generate a question.

        Args:
            state (dict): The current graph state

        Returns:
            str: Binary decision for next node to call
        """
        logger.info("---ASSESS GRADED DOCUMENTS---")
        filtered_documents = state["documents"]

        if not filtered_documents:
            # All documents have been filtered check_relevance
            # We will re-generate a new query
            logger.info("---DECISION: ALL DOCUMENTS ARE NOT RELEVANT, TRANSFORM QUERY---")
            return "transform_query"
        else:
            # We have relevant documents, so generate answer
            logger.info("---DECISION: GENERATE---")
            return "generate"

    async def grade_generation_v_documents_and_question(self, state: RAGAgentState, config: RunnableConfig) -> Literal["not supported", "useful", "not useful"]:
        """
        Determines whether the generation is grounded in the document and answers question.

        Args:
            state (dict): The current graph state

        Returns:
            str: Decision for next node to call
        """
        logger.info("---CHECK HALLUCINATIONS---")
        question = state["question"]
        documents = state["documents"]
        generation = state["generation"]
        
        context = "\n\n".join(documents)

        # Check hallucination
        hallucination_grader = self.grader_model.with_structured_output(GradeHallucinations)
        
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

# Define the graph export
graph = DeepSightRAGAgent(RAGAgentConfig(
    model_name="gpt-5.2",
    dataset_ids=[],
    mcp_server_url="http://localhost:9382/mcp/"
)).graph