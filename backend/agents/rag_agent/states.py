"""
LangGraph state definitions for RAG agent.

Refactored to match the requested GraphState schema:
- question: str
- generation: str
- documents: list[str]

Inherits from CopilotKitState for frontend compatibility (messages support).
"""

from typing import Any, List, Optional

from pydantic import Field
from copilotkit import CopilotKitState


class RAGAgentState(CopilotKitState):
    """
    State for the RAG agent aligning with the requested GraphState schema.
    
    Attributes:
        question: The user's question or the rewritten query.
        generation: The LLM generated answer.
        documents: List of retrieved document contents.
        
    CopilotKit Integration:
        messages: Maintained by CopilotKitState for chat history.
    """

    # --- Core GraphState Attributes ---
    question: str = ""
    original_question: str | None = None  # Preserve the user's initial question
    generation: str = ""
    queries: List[str] = [] # List of generated queries for multi-angle search
    documents: List[str] = [] # List of all relevant document contents
    new_documents: List[str] = [] # Newly retrieved documents to be graded separately
    semantic_groups: List[dict] = [] # Structured semantic groups (lightweight mapping) instead of heavy string
    # reordered_context is removed to save bandwidth; generate node reconstructs it from groups + docs

    # --- CopilotKit AG-UI protocol fields for UI Rendering ---
    current_step: str | None = None
    iteration_count: int = 0  # Track iterations to handle recursion limit gracefully
    graded_documents: list[dict[str, Any]] | None = None
    query_rewrites: list[str] | None = None
    synthesis_progress: int | None = None
    total_tool_calls: int | None = None
    agent_reasoning: str | None = None



