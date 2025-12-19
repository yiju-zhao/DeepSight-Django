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
    format_rewrite_irrelevant_prompt,
    format_rewrite_incomplete_prompt,
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
        workflow.add_node("grade_relevance", self.grade_relevance)
        workflow.add_node("grade_completeness", self.grade_completeness)
        workflow.add_node("generate", self.generate)
        workflow.add_node("rewrite_irrelevant", self.rewrite_irrelevant)
        workflow.add_node("rewrite_incomplete", self.rewrite_incomplete)

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

        workflow.add_edge("retrieve", "grade_relevance")
        
        workflow.add_conditional_edges(
            "grade_relevance",
            self.decide_after_relevance,
            {
                "rewrite_irrelevant": "rewrite_irrelevant",
                "grade_completeness": "grade_completeness",
            },
        )
        
        workflow.add_conditional_edges(
            "grade_completeness",
            self.decide_after_completeness,
            {
                "rewrite_incomplete": "rewrite_incomplete",
                "generate": "generate",
            },
        )
        
        workflow.add_edge("rewrite_irrelevant", "retrieve")
        workflow.add_edge("rewrite_incomplete", "retrieve")
        
        workflow.add_conditional_edges(
            "generate",
            self.grade_generation_v_documents_and_question,
            {
                "not supported": "generate", # Loop back to regenerate (simple retry)
                "useful": END,
                "not useful": "rewrite_incomplete", # If not useful, try to find more info
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

    async def grade_relevance(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Filter retrieved documents for relevance.
        """
        logger.info("---CHECKING RELEVANCE---")
        question = state["question"]
        documents = state["documents"]
        
        filtered_docs = []
        graded_docs_meta = []
        structured_grader = self.grader_model.with_structured_output(GradeDocuments)

        for d in documents:
            prompt = format_grade_documents_prompt(question=question, context=d)
            score = await structured_grader.ainvoke([HumanMessage(content=prompt)], config)
            is_relevant = score.binary_score.lower() == "yes"
            
            graded_docs_meta.append({
                "content": d[:100] + "...",
                "relevant": is_relevant,
                "reason": "Graded by LLM"
            })
            if is_relevant:
                filtered_docs.append(d)

        logger.info(f"---FILTERED {len(filtered_docs)}/{len(documents)} RELEVANT DOCS---")

        return {
            "documents": filtered_docs, 
            "graded_documents": graded_docs_meta,
            "current_step": "grading_relevance"
        }

    async def grade_completeness(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Check if the current collection is sufficient for the original question.
        """
        logger.info("---CHECKING COMPLETENESS---")
        original_question = state["original_question"]
        documents = state["documents"]
        
        context = "\n\n".join(documents)
        completeness_grader = self.grader_model.with_structured_output(GradeCompleteness)
        
        prompt = format_grade_completeness_prompt(question=original_question, context=context)
        score = await completeness_grader.ainvoke([HumanMessage(content=prompt)], config)
        
        logger.info(f"---COMPLETENESS: {score.is_complete}---")
        
        return {
            "is_complete": score.is_complete,
            "agent_reasoning": f"Research incomplete. Missing: {score.missing_info}" if not score.is_complete else "Research complete.",
            "current_step": "grading_completeness"
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

    async def rewrite_irrelevant(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Broaden search when initial results were irrelevant.
        """
        logger.info("---REWRITE IRRELEVANT---")
        question = state["question"]
        iteration_count = state.get("iteration_count", 0) + 1
        
        prompt = format_rewrite_irrelevant_prompt(question=question)
        response = await self.response_model.ainvoke([HumanMessage(content=prompt)], config)
        better_question = response.content
        
        logger.info(f"---BROADER QUESTION: {better_question}---")
        
        return {
            "question": better_question,
            "iteration_count": iteration_count,
            "current_step": "rewriting_irrelevant",
            "agent_reasoning": f"No relevant found. Broadening search: {better_question}"
        }

    async def rewrite_incomplete(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Target missing info when research is incomplete.
        """
        logger.info("---REWRITE INCOMPLETE---")
        original_question = state["original_question"]
        documents = state["documents"]
        iteration_count = state.get("iteration_count", 0) + 1
        
        current_context = "\n\n".join([d[:200] + "..." for d in documents])
        prompt = format_rewrite_incomplete_prompt(question=original_question, current_context=current_context)
        response = await self.response_model.ainvoke([HumanMessage(content=prompt)], config)
        better_question = response.content
        
        logger.info(f"---TARGETED QUESTION: {better_question}---")
        
        return {
            "question": better_question,
            "iteration_count": iteration_count,
            "current_step": "rewriting_incomplete",
            "agent_reasoning": f"Research incomplete. Targeting gaps: {better_question}"
        }

    # --- Edges ---

    def decide_after_relevance(self, state: RAGAgentState) -> Literal["rewrite_irrelevant", "grade_completeness"]:
        """
        Routes based on whether any relevant documents were found.
        """
        logger.info("---DECIDE AFTER RELEVANCE---")
        iteration_count = state.get("iteration_count", 0)
        
        # Force progression if approaching recursion limit
        if iteration_count >= 20:
            logger.warning(f"---ITERATION LIMIT APPROACHING ({iteration_count}/25), FORCING PROGRESSION TO COMPLETENESS CHECK---")
            return "grade_completeness"
        
        if not state["documents"]:
            logger.info("---DECISION: NO RELEVANT DOCS, REWRITE IRRELEVANT---")
            return "rewrite_irrelevant"
        
        logger.info("---DECISION: RELEVANT DOCS FOUND, CHECK COMPLETENESS---")
        return "grade_completeness"

    def decide_after_completeness(self, state: RAGAgentState) -> Literal["rewrite_incomplete", "generate"]:
        """
        Routes based on whether the collection is complete.
        """
        logger.info("---DECIDE AFTER COMPLETENESS---")
        iteration_count = state.get("iteration_count", 0)
        is_complete = state.get("is_complete", False)

        # Force generation if approaching recursion limit
        if iteration_count >= 20:
            logger.warning(f"---ITERATION LIMIT APPROACHING ({iteration_count}/25), FORCING GENERATION---")
            return "generate"

        if is_complete:
            logger.info("---DECISION: COMPLETE, GENERATE---")
            return "generate"
        else:
            logger.info("---DECISION: INCOMPLETE, REWRITE INCOMPLETE---")
            return "rewrite_incomplete"

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