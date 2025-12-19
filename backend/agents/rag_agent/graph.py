import json
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
    format_grade_completeness_prompt,
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

class GradeCompleteness(BaseModel):
    """Assess if the retrieved documents are sufficient to answer the original question."""
    is_complete: bool = Field(description="The collective documents are sufficient to answer the original question")
    missing_info: str | None = Field(description="Description of what information is still missing if not complete")

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
        # Note: recursion_limit is set in RunnableConfig when invoking the graph, not here
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
                "original_question": question, # Preserve the starting intent
                "documents": [], 
                "generation": "",
                "is_complete": False,
                "iteration_count": 0,
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
        """
        logger.info("---RETRIEVE---")
        question = state["question"]
        current_docs = state.get("documents", [])
        
        # Get tools from context variable (NOT from config to avoid circular refs)
        tools = current_retrieval_tools.get()
        if not tools:
            # Fallback: create tools from config (for standalone usage)
            tools = await create_mcp_retrieval_tools(
                dataset_ids=self.config.dataset_ids,
                mcp_server_url=self.config.mcp_server_url
            )
        
        new_documents = []
        if tools:
            # Call the retrieval tool directly instead of bind_tools()
            for tool in tools:
                if "retrieval" in tool.name.lower() or "search" in tool.name.lower():
                    try:
                        # Invoke the tool directly with the question
                        result = await tool.ainvoke({"question": question}, {**config, "callbacks": []})
                        # Format and add the result
                        content = format_tool_content(result)
                        if content:
                            new_documents.append(content)
                        logger.info(f"Retrieved {len(new_documents)} new documents")
                        break  # Use the first matching retrieval tool
                    except Exception as e:
                        logger.error(f"Error calling retrieval tool: {e}")

        # Deduplicate and accumulate
        seen = set(current_docs)
        combined_docs = list(current_docs)
        for doc in new_documents:
            if doc not in seen:
                combined_docs.append(doc)
                seen.add(doc)

        return {
            "documents": combined_docs, 
            "question": question, 
            "current_step": "retrieving"
        }

    async def grade_documents(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Check document relevance and collection completeness.
        """
        logger.info("---CHECKING RELEVANCE AND COMPLETENESS---")
        original_question = state["original_question"]
        documents = state["documents"]
        
        # 1. Relevance Score (Optional: Could filter here, but we'll focus on completeness)
        # We'll just grade for UI feedback
        graded_docs_meta = []
        for d in documents:
            graded_docs_meta.append({
                "content": d[:100] + "...",
                "relevant": True, # For now, keep all retrieved
                "reason": "Retrieved from source"
            })

        # 2. Check Completeness
        context = "\n\n".join(documents)
        completeness_grader = self.grader_model.with_structured_output(GradeCompleteness)
        
        prompt = format_grade_completeness_prompt(question=original_question, context=context)
        score = await completeness_grader.ainvoke([HumanMessage(content=prompt)], config)
        
        is_complete = score.is_complete
        missing_info = score.missing_info
        
        logger.info(f"---COMPLETENESS: {is_complete}---")
        if not is_complete:
            logger.info(f"---MISSING INFO: {missing_info}---")

        return {
            "documents": documents, 
            "graded_documents": graded_docs_meta,
            "is_complete": is_complete,
            "agent_reasoning": f"Checks completeness: {is_complete}. " + (f"Missing: {missing_info}" if missing_info else "Ready to generate."),
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
        Target missing information using a context-aware rewrite.
        """
        logger.info("---TRANSFORM QUERY---")
        original_question = state["original_question"]
        documents = state["documents"]
        iteration_count = state.get("iteration_count", 0) + 1
        
        # Provide what we already know to the rewriter
        current_context = "\n\n".join([d[:200] + "..." for d in documents]) if documents else "Nothing yet."
        
        prompt = format_rewrite_question_prompt(question=original_question, current_context=current_context)
        response = await self.response_model.ainvoke([HumanMessage(content=prompt)], config)
        better_question = response.content
        
        logger.info(f"---BETTER QUESTION: {better_question}---")
        
        return {
            "question": better_question,
            "iteration_count": iteration_count,
            "current_step": "rewriting",
            "agent_reasoning": f"Searching for missing info: {better_question}"
        }

    # --- Edges ---

    def decide_to_generate(self, state: RAGAgentState) -> Literal["transform_query", "generate"]:
        """
        Determines whether to generate an answer, or re-generate a question.
        
        Checks iteration count and completeness flag to decide next step.
        """
        logger.info("---ASSESSING NEXT STEP---")
        iteration_count = state.get("iteration_count", 0)
        is_complete = state.get("is_complete", False)

        # Force generation if approaching recursion limit (20 out of 25)
        if iteration_count >= 20:
            logger.warning(f"---ITERATION LIMIT APPROACHING ({iteration_count}/25), FORCING GENERATION---")
            return "generate"

        if is_complete:
            logger.info("---DECISION: COMPLETE, GENERATE---")
            return "generate"
        else:
            logger.info("---DECISION: INCOMPLETE, TRANSFORM QUERY---")
            return "transform_query"

    async def grade_generation_v_documents_and_question(self, state: RAGAgentState, config: RunnableConfig) -> Literal["not supported", "useful", "not useful"]:
        """
        Determines whether the generation is grounded in the document and answers question.
        
        Checks iteration count to prevent infinite loops - if approaching recursion limit,
        accepts the current generation to produce output.

        Args:
            state (dict): The current graph state

        Returns:
            str: Decision for next node to call
        """
        logger.info("---CHECK HALLUCINATIONS---")
        question = state["question"]
        documents = state["documents"]
        generation = state["generation"]
        iteration_count = state.get("iteration_count", 0)
        
        # Force acceptance if approaching recursion limit (20 out of 25)
        if iteration_count >= 20:
            logger.warning(f"---ITERATION LIMIT APPROACHING ({iteration_count}/25), ACCEPTING GENERATION---")
            return "useful"
        
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