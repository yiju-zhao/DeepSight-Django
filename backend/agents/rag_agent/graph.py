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
    format_synthesis_prompt,
    format_grade_documents_prompt,
    format_grade_completeness_prompt,
    format_rewrite_irrelevant_prompt,
    format_rewrite_incomplete_prompt,
    format_rewrite_continuation_prompt,
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
    new_docs_contribute: bool = Field(description="Whether newly retrieved documents contribute to completing the story (True if no new docs)")
    is_complete: bool = Field(description="The collective documents are sufficient to answer the original question")
    missing_info: str | None = Field(description="Description of what information is still missing if not complete")
    search_advice: str | None = Field(description="Specific advice on what to search for next if incomplete")

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
        logger.info(f"Initializing models - Nano: {self.config.nano_model_name}, Full: {self.config.model_name}")
        self.response_model = init_chat_model(
            model=f"openai:{self.config.nano_model_name}",
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
        workflow.add_node("rewrite_continuation", self.rewrite_continuation)

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

        workflow.add_conditional_edges(
            "retrieve",
            self.decide_after_retrieve,
            {
                "grade_relevance": "grade_relevance",
                "grade_completeness": "grade_completeness",
            },
        )
        
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
                "rewrite_continuation": "rewrite_continuation",
                "generate": "generate",
            },
        )
        
        workflow.add_edge("rewrite_irrelevant", "retrieve")
        workflow.add_edge("rewrite_incomplete", "retrieve")
        workflow.add_edge("rewrite_continuation", "retrieve")
        
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
                "new_documents": [],
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
        
        raw_new_documents = []
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
                            raw_new_documents.append(content)
                        logger.info(f"Retrieved {len(raw_new_documents)} new documents")
                        break  # Use the first matching retrieval tool
                    except Exception as e:
                        logger.error(f"Error calling retrieval tool: {e}")

        # Filter out duplicates against existing docs
        seen_existing = set(current_docs)
        unique_new_docs = []
        for doc in raw_new_documents:
            if doc not in seen_existing:
                unique_new_docs.append(doc)
        
        # Note: We do NOT append to "documents" yet. grade_relevance will do that.
        
        return {
            "new_documents": unique_new_docs,
            "question": question, 
            "current_step": "retrieving"
        }

    async def grade_relevance(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Filter retrieved documents for relevance.
        Only grades NEW documents to save tokens and time.
        """
        logger.info("---CHECKING RELEVANCE---")
        question = state["question"]
        new_documents = state["new_documents"]
        existing_documents = state["documents"]
        
        relevant_new_docs = []
        graded_docs_meta = []
        structured_grader = self.grader_model.with_structured_output(GradeDocuments)

        for d in new_documents:
            prompt = format_grade_documents_prompt(question=question, context=d)
            score = await structured_grader.ainvoke([HumanMessage(content=prompt)], config)
            is_relevant = score.binary_score.lower() == "yes"
            
            graded_docs_meta.append({
                "content": d[:100] + "...",
                "relevant": is_relevant,
                "reason": "Graded by LLM"
            })
            if is_relevant:
                relevant_new_docs.append(d)

        logger.info(f"---FILTERED {len(relevant_new_docs)}/{len(new_documents)} RELEVANT NEW DOCS---")

        return {
            "documents": existing_documents + relevant_new_docs, # Accumulate for first iteration
            "new_documents": relevant_new_docs, # Also store for potential completeness eval
            "graded_documents": graded_docs_meta,
            "current_step": "grading_relevance"
        }

    async def grade_completeness(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Check if the current collection is sufficient and if new docs contribute.
        """
        logger.info("---CHECKING COMPLETENESS---")
        original_question = state["original_question"]
        existing_documents = state.get("documents", [])
        new_documents = state.get("new_documents", [])
        
        # Prepare contexts for evaluation
        existing_context = "\n\n".join(existing_documents) if existing_documents else "[No existing documents]"
        new_context = "\n\n".join(new_documents) if new_documents else "[No new documents]"
        
        completeness_grader = self.grader_model.with_structured_output(GradeCompleteness)
        
        prompt = format_grade_completeness_prompt(
            question=original_question, 
            existing_context=existing_context,
            new_context=new_context
        )
        score = await completeness_grader.ainvoke([HumanMessage(content=prompt)], config)
        
        # Decision: append new docs only if they contribute
        if new_documents and score.new_docs_contribute:
            logger.info(f"---NEW DOCS CONTRIBUTE: Appending {len(new_documents)} docs---")
            updated_documents = existing_documents + new_documents
        else:
            if new_documents:
                logger.info(f"---NEW DOCS DO NOT CONTRIBUTE: Discarding {len(new_documents)} docs---")
            updated_documents = existing_documents
        
        logger.info(f"---COMPLETENESS: {score.is_complete}, Total docs: {len(updated_documents)}---")
        
        return {
            "documents": updated_documents,
            "new_documents": [], # Clear buffer after processing
            "is_complete": score.is_complete,
            "search_advice": score.search_advice,
            "agent_reasoning": f"Research incomplete. Advice: {score.search_advice}" if not score.is_complete else "Research complete.",
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
        Target missing topic info when research is incomplete (MISSING_TOPIC case).
        """
        logger.info("---REWRITE INCOMPLETE (MISSING TOPIC)---")
        original_question = state["original_question"]
        documents = state["documents"]
        search_advice = state.get("search_advice", "Look for missing details.")
        iteration_count = state.get("iteration_count", 0) + 1
        
        current_context = "\n\n".join([d[:200] + "..." for d in documents])
        prompt = format_rewrite_incomplete_prompt(
            question=original_question, 
            current_context=current_context,
            search_advice=search_advice
        )
        response = await self.response_model.ainvoke([HumanMessage(content=prompt)], config)
        better_question = response.content
        
        logger.info(f"---TARGETED QUESTION: {better_question}---")
        
        return {
            "question": better_question,
            "iteration_count": iteration_count,
            "continuation_mode": False,
            "current_step": "rewriting_incomplete",
            "agent_reasoning": f"Research incomplete. Targeting: {better_question}"
        }

    async def rewrite_continuation(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Find chunk continuation when content is TRUNCATED.
        Uses phrases from the END of truncated content to find adjacent chunks.
        """
        logger.info("---REWRITE CONTINUATION (TRUNCATED)---")
        original_question = state["original_question"]
        documents = state["documents"]
        iteration_count = state.get("iteration_count", 0) + 1
        
        # Get the last ~500 chars of the most recent document (likely truncated)
        if documents:
            last_doc = documents[-1]
            last_portion = last_doc[-500:] if len(last_doc) > 500 else last_doc
        else:
            last_portion = ""
        
        prompt = format_rewrite_continuation_prompt(
            question=original_question, 
            last_portion=last_portion
        )
        response = await self.response_model.ainvoke([HumanMessage(content=prompt)], config)
        continuation_query = response.content
        
        logger.info(f"---CONTINUATION QUERY: {continuation_query}---")
        
        return {
            "question": continuation_query,
            "iteration_count": iteration_count,
            "continuation_mode": True,
            "current_step": "rewriting_continuation",
            "agent_reasoning": f"Content truncated. Searching for continuation: {continuation_query}"
        }

    # --- Edges ---

    def decide_after_retrieve(self, state: RAGAgentState) -> Literal["grade_relevance", "grade_completeness"]:
        """
        Routes after retrieval:
        - First time (no existing docs): grade for relevance
        - Subsequent times: directly check completeness (contribution-based)
        """
        logger.info("---DECIDE AFTER RETRIEVE---")
        existing_documents = state.get("documents", [])
        
        if not existing_documents:
            # First retrieval: check relevance
            logger.info("---DECISION: FIRST RETRIEVAL, GRADE RELEVANCE---")
            return "grade_relevance"
        else:
            # Have existing docs: skip relevance, directly evaluate contribution
            logger.info("---DECISION: SUBSEQUENT RETRIEVAL, GRADE COMPLETENESS (CONTRIBUTION)---")
            return "grade_completeness"

    def decide_after_relevance(self, state: RAGAgentState) -> Literal["rewrite_irrelevant", "grade_completeness"]:
        """
        Routes based on whether any relevant documents were found.
        """
        logger.info("---DECIDE AFTER RELEVANCE---")
        iteration_count = state.get("iteration_count", 0)
        
        # Force progression if approaching recursion limit
        if iteration_count >= self.config.max_iterations:
            logger.warning(f"---ITERATION LIMIT REACHED ({iteration_count}/{self.config.max_iterations}), FORCING PROGRESSION TO COMPLETENESS CHECK---")
            return "grade_completeness"
        
        if not state["documents"]:
            # If we have NO relevant documents at all (new or old), we need to broaden request
            logger.info("---DECISION: NO RELEVANT DOCS, REWRITE IRRELEVANT---")
            return "rewrite_irrelevant"
        
        logger.info("---DECISION: RELEVANT DOCS FOUND, CHECK COMPLETENESS---")
        return "grade_completeness"

    def decide_after_completeness(self, state: RAGAgentState) -> Literal["rewrite_incomplete", "rewrite_continuation", "generate"]:
        """
        Routes based on whether the collection is complete.
        Differentiates between missing topics and truncated content.
        """
        logger.info("---DECIDE AFTER COMPLETENESS---")
        iteration_count = state.get("iteration_count", 0)
        is_complete = state.get("is_complete", False)
        search_advice = state.get("search_advice", "")

        # Force generation if approaching recursion limit
        if iteration_count >= self.config.max_iterations:
            logger.warning(f"---ITERATION LIMIT REACHED ({iteration_count}/{self.config.max_iterations}), FORCING GENERATION---")
            return "generate"

        if is_complete:
            logger.info("---DECISION: COMPLETE, GENERATE---")
            return "generate"
        else:
            # Check if truncated or missing topic based on search_advice prefix
            if search_advice and search_advice.startswith("[TRUNCATED]"):
                logger.info("---DECISION: TRUNCATED CONTENT, REWRITE CONTINUATION---")
                return "rewrite_continuation"
            else:
                logger.info("---DECISION: MISSING TOPIC, REWRITE INCOMPLETE---")
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
        
        # Force acceptance if approaching recursion limit
        if iteration_count >= self.config.max_iterations:
            logger.warning(f"---ITERATION LIMIT REACHED ({iteration_count}/{self.config.max_iterations}), ACCEPTING GENERATION---")
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
