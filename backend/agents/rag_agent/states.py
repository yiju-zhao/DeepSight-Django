"""
LangGraph state definitions for RAG agent.

Refactored to match the requested GraphState schema:
- question: str
- generation: str
- documents: list[str]

Uses TypedDict instead of Pydantic model to avoid serialization recursion issues
in ag_ui_langgraph.
"""

from typing import Any, Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class RAGAgentState(TypedDict):
    """
    State for the RAG agent aligning with the requested GraphState schema.
    Defined as TypedDict to ensure safe serialization.
    
    Attributes:
        messages: Chat history (reducer: add_messages)
        question: The user's question or the rewritten query.
        generation: The LLM generated answer.
        documents: List of retrieved document contents.
    """
    
    # --- CopilotKit Integration ---
    messages: Annotated[list[BaseMessage], add_messages]

    # --- Core GraphState Attributes ---
    question: str
    generation: str
    documents: list[str]

    # --- CopilotKit AG-UI protocol fields for UI Rendering ---
    current_step: str | None
    iteration_count: int | None
    graded_documents: list[dict[str, Any]] | None
    query_rewrites: list[str] | None
    synthesis_progress: int | None
    total_tool_calls: int | None
    agent_reasoning: str | None


# Type alias for backward compatibility
RAGReActState = RAGAgentState
