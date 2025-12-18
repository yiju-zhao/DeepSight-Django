"""
LangGraph state definitions for RAG agent.

Uses LangGraph's MessagesState pattern for compatibility with built-in
tools_condition and ToolNode, while extending with additional fields
needed for the RAG workflow.

Includes CopilotKit AG-UI protocol fields for real-time agent state rendering.
"""

from typing import Any

from copilotkit import CopilotKitState


class RAGAgentState(CopilotKitState):
    """
    State for the RAG agent using LangGraph MessagesState pattern.

    Inherits from MessagesState which provides:
    - messages: Annotated[list[BaseMessage], add_messages]

    The add_messages annotation means new messages are appended to the list
    rather than replacing it.

    Additional fields for RAG workflow:
    - question: Original user question (for reference in synthesis)
    - retrieved_chunks: Accumulated chunks for citation extraction

    CopilotKit AG-UI protocol fields for state rendering:
    - current_step: Current execution step
    - iteration_count: Number of retrieval iterations
    - graded_documents: Document grading results with relevance scores
    - query_rewrites: History of query reformulations
    - synthesis_progress: Progress percentage for final answer generation
    - total_tool_calls: Total number of tool invocations
    - agent_reasoning: Current reasoning/status message

    Example:
        >>> initial_state = {
        ...     "messages": [HumanMessage(content="What is deep learning?")],
        ...     "question": "What is deep learning?",
        ...     "retrieved_chunks": [],
        ...     "current_step": "idle",
        ...     "iteration_count": 0,
        ... }
    """

    # Original user question for reference during synthesis
    question: str

    # Accumulated retrieved chunks for citation extraction after answer generation
    # Format: [{"chunk_id": ..., "doc_name": ..., "content": ..., "similarity": ...}]
    retrieved_chunks: list[dict[str, Any]]

    # CopilotKit AG-UI protocol fields
    # Current execution step: idle, analyzing, retrieving, grading, rewriting, synthesizing, complete
    current_step: str | None = None

    # Number of retrieval iterations performed
    iteration_count: int | None = None

    # Graded documents with relevance scores
    # Format: [{"content": ..., "score": ..., "relevant": bool, "reason": ...}]
    graded_documents: list[dict[str, Any]] | None = None

    # History of query rewrites for improved retrieval
    query_rewrites: list[str] | None = None

    # Synthesis progress percentage (0-100)
    synthesis_progress: int | None = None

    # Total number of tool calls made during execution
    total_tool_calls: int | None = None

    # Current reasoning or status message for UI display
    agent_reasoning: str | None = None


# Type alias for backward compatibility
RAGReActState = RAGAgentState
