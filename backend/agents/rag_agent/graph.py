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
    format_planning_prompt,
    format_reorder_prompt,
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

class SemanticGroup(BaseModel):
    """A logical group of document chunks."""
    group_name: str = Field(description="Brief name or theme of the group")
    description: str = Field(description="Short description of what these chunks collectively cover")
    chunk_ids: list[int] = Field(description="Ordered list of chunk IDs belonging to this group")

class ReorderedContext(BaseModel):
    """The structured mapping of chunks into semantic groups."""
    groups: list[SemanticGroup] = Field(description="List of semantic groups containing ordered chunk IDs")


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
        workflow.add_node("planning", self.planning)
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade_relevance", self.grade_relevance)
        workflow.add_node("reorder", self.reorder)
        workflow.add_node("generate", self.generate)

        # Build graph
        workflow.add_edge(START, "initialize_request")
        
        # If initialization fails (no input), end
        workflow.add_conditional_edges(
            "initialize_request",
            self.check_initialization,
            {
                "planning": "planning",
                "end": END
            }
        )

        workflow.add_edge("planning", "retrieve")
        workflow.add_edge("retrieve", "grade_relevance")
        
        workflow.add_conditional_edges(
            "grade_relevance",
            self.decide_after_relevance,
            {
                "planning": "planning",
                "reorder": "reorder",
                "generate": "generate",
            },
        )
        
        workflow.add_edge("reorder", "generate")
        workflow.add_edge("generate", END)

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
            # Reset state for new turn to avoid state bloat and frontend lag
            # This prevents large data from previous turns (documents, reasoning, etc.) 
            # from accumulating and slowing down the JSON serialization/parsing.
            return {
                "question": question, 
                "original_question": question,
                "queries": [],
                "documents": [], 
                "new_documents": [],
                "reordered_context": "",
                "generation": "",
                "iteration_count": 0,
                "current_step": "analyzing",
                "graded_documents": None,
                "query_rewrites": None,
                "agent_reasoning": None,
                "synthesis_progress": None,
                "total_tool_calls": None,
                "semantic_groups": []
            }
        
        # If no question is found, return empty to trigger check_initialization -> end
        return {}

    def check_initialization(self, state: RAGAgentState) -> Literal["planning", "end"]:
        """Check if we have a valid question to start retrieval."""
        if state.get("question"):
            return "planning"
        logger.info("No question found, ending.")
        return "end"

    async def planning(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Generate multiple search queries from different angles.
        """
        logger.info("---PLANNING---")
        question = state["question"]
        iteration_count = state.get("iteration_count", 0)
        previous_queries = state.get("queries", [])
        
        prompt = format_planning_prompt(question=question, previous_queries=previous_queries if iteration_count > 0 else None)
        
        response = await self.response_model.ainvoke([HumanMessage(content=prompt)], config)
        try:
            # Expecting a JSON list of strings
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            
            queries = json.loads(content)
            if not isinstance(queries, list):
                queries = [content]
        except Exception as e:
            logger.error(f"Error parsing planning queries: {e}")
            queries = [question]
        
        logger.info(f"Planned queries: {queries}")
        
        return {
            "queries": queries,
            "iteration_count": iteration_count + 1,
            "current_step": "planning"
        }

    async def retrieve(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Retrieve documents by executing multiple planned queries.
        """
        logger.info("---RETRIEVE---")
        queries = state.get("queries", [state["question"]])
        
        # Get tools from context variable
        tools = current_retrieval_tools.get()
        if not tools:
            tools = await create_mcp_retrieval_tools(
                dataset_ids=self.config.dataset_ids,
                mcp_server_url=self.config.mcp_server_url
            )
        
        all_new_documents = []
        if tools:
            retrieval_tool = next((t for t in tools if "retrieval" in t.name.lower() or "search" in t.name.lower()), None)
            if retrieval_tool:
                for q in queries:
                    try:
                        logger.info(f"Retrieving for query: {q}")
                        result = await retrieval_tool.ainvoke({"question": q}, {**config, "callbacks": []})
                        # Format and add the result
                        content = format_tool_content(result)
                        if content:
                            # CRITICAL: Truncate content to prevent frontend state bloat
                            # Chunks for RAG are typically 1k-4k tokens, 3000 chars is a safe snippet
                            if len(content) > 3000:
                                content = content[:3000] + "..."
                            all_new_documents.append(content)
                    except Exception as e:
                        logger.error(f"Error calling retrieval tool for query '{q}': {e}")

        # Deduplicate results (simple string comparison)
        unique_new_docs = list(dict.fromkeys(all_new_documents))
        
        logger.info(f"Retrieved {len(unique_new_docs)} unique documents from {len(queries)} queries")
        
        return {
            "new_documents": unique_new_docs,
            "current_step": "retrieving"
        }

    async def grade_relevance(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Filter retrieved documents for relevance to the ORIGINAL question.
        Merged with previously found documents.
        """
        logger.info("---CHECKING RELEVANCE---")
        original_question = state["original_question"]
        new_documents = state["new_documents"]
        existing_documents = state.get("documents", [])
        
        relevant_new_docs = []
        graded_docs_meta = []
        structured_grader = self.grader_model.with_structured_output(GradeDocuments)

        for d in new_documents:
            # Skip if already in existing_documents
            if d in existing_documents:
                continue
                
            prompt = format_grade_documents_prompt(question=original_question, context=d)
            score = await structured_grader.ainvoke([HumanMessage(content=prompt)], config)
            is_relevant = score.binary_score.lower() == "yes"
            
            graded_docs_meta.append({
                "content": d[:100] + "...",
                "relevant": is_relevant,
                "reason": "Graded by LLM"
            })
            if is_relevant:
                relevant_new_docs.append(d)

        all_relevant_docs = existing_documents + relevant_new_docs
        logger.info(f"---FILTERED {len(relevant_new_docs)} NEW RELEVANT DOCS. TOTAL: {len(all_relevant_docs)}---")

        return {
            "documents": all_relevant_docs,
            "new_documents": [], # Clear buffer
            "graded_documents": graded_docs_meta,
            "current_step": "grading_relevance"
        }

    async def reorder(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Semantically reorder and group retrieved chunks using ID mapping.
        """
        logger.info("---REORDERING---")
        original_question = state["original_question"]
        documents = state["documents"]
        
        if not documents:
            return {"current_step": "reordering"}
            
        # 1. Assign IDs to documents for the LLM to map
        id_mapped_docs = {i: doc for i, doc in enumerate(documents, 1)}
        formatted_context = ""
        for i, doc in id_mapped_docs.items():
            formatted_context += f"ID: {i}\nContent: {doc}\n\n"
            
        prompt = format_reorder_prompt(question=original_question, context=formatted_context)
        
        # 2. Call LLM with structured output
        structured_reorderer = self.grader_model.with_structured_output(ReorderedContext)
        result = await structured_reorderer.ainvoke([HumanMessage(content=prompt)], config)
        
        # 3. Create lightweight semantic groups for state (UI rendering)
        # We DO NOT construct the full string here to avoid doubling state size
        final_groups = []
        assigned_chunk_ids = set()
        
        for group in result.groups:
            # Filter IDs to ensure each chunk is only used once
            valid_chunk_ids = []
            for chunk_id in group.chunk_ids:
                if chunk_id in id_mapped_docs and chunk_id not in assigned_chunk_ids:
                    valid_chunk_ids.append(chunk_id)
                    assigned_chunk_ids.add(chunk_id)
            
            if valid_chunk_ids:
                final_groups.append({
                    "group_name": group.group_name,
                    "description": group.description,
                    "chunk_ids": valid_chunk_ids
                })
        
        logger.info(f"Reordering complete. Created {len(final_groups)} semantic groups.")
        
        return {
            "semantic_groups": final_groups,
            "current_step": "reordering"
        }

    async def generate(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """
        Generate final answer using dynamic content reconstruction.
        """
        logger.info("---GENERATE---")
        question = state["original_question"]
        documents = state["documents"]
        semantic_groups = state.get("semantic_groups", [])
        
        # Reconstruct context from groups + documents (only if needed for generation)
        if not semantic_groups and not documents:
            generation = "I'm sorry, but I couldn't find any relevant information to answer your question after several search attempts."
        else:
            if semantic_groups:
                # Rebuild structured context on the fly
                context_parts = []
                # Map 1-based IDs back to 0-based index
                id_to_doc = {i: doc for i, doc in enumerate(documents, 1)}
                
                for group in semantic_groups:
                    group_text = f"### {group['group_name']}\n*{group['description']}*\n\n"
                    chunks = []
                    for cid in group['chunk_ids']:
                        if cid in id_to_doc:
                            chunks.append(id_to_doc[cid])
                    if chunks:
                        group_text += "\n\n".join(chunks)
                        context_parts.append(group_text)
                context = "\n\n---\n\n".join(context_parts)
            else:
                context = "\n\n".join(documents)
                
            prompt = format_synthesis_prompt(question=question, context=context)
            response = await self.synthesis_model.ainvoke([HumanMessage(content=prompt)], config)
            generation = response.content
        
        return {
            "generation": generation,
            "messages": [AIMessage(content=generation)],
            "documents": [], # Clear massive doc list
            "semantic_groups": [], # Clear groups
            "graded_documents": None, 
            "current_step": "synthesizing",
            "synthesis_progress": 100
        }

    # --- Edges ---

    def decide_after_relevance(self, state: RAGAgentState) -> Literal["planning", "reorder", "generate"]:
        """
        Routes based on whether relevant documents were found and iteration count.
        """
        logger.info("---DECIDE AFTER RELEVANCE---")
        iteration_count = state.get("iteration_count", 0)
        has_documents = len(state.get("documents", [])) > 0
        
        if has_documents:
            logger.info("---DECISION: RELEVANT DOCS FOUND, REORDERING---")
            return "reorder"
        
        if iteration_count < 3:
            logger.info(f"---DECISION: NO RELEVANT DOCS (Iter {iteration_count}/3), RE-PLANNING---")
            return "planning"
        
        logger.info("---DECISION: NO RELEVANT DOCS AFTER 3 ITERS, FORCING GENERATION (Failure message)---")
        return "generate"

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
