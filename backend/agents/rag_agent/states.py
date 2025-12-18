"""
LangGraph state definitions for RAG agent.

Refactored to match the requested GraphState schema:
- question: str
- generation: str
- documents: List[str]

Inherits from CopilotKitState for frontend compatibility (messages support).
"""

from typing import Any, List, Optional

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
    question: str
    generation: str
    documents: List[str]

    # --- CopilotKit AG-UI protocol fields for UI Rendering ---
    current_step: str | None = None
    iteration_count: int | None = None
    graded_documents: list[dict[str, Any]] | None = None
    query_rewrites: list[str] | None = None
    synthesis_progress: int | None = None
    total_tool_calls: int | None = None
    agent_reasoning: str | None = None


# Type alias for backward compatibility
RAGReActState = RAGAgentState
