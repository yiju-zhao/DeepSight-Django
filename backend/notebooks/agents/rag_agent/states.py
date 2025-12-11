"""
LangGraph state definitions for RAG agent.

Uses LangGraph's MessagesState pattern for compatibility with built-in
tools_condition and ToolNode, while extending with additional fields
needed for the RAG workflow.
"""

from typing import Any

from langgraph.graph import MessagesState


class RAGAgentState(MessagesState):
    """
    State for the RAG agent using LangGraph MessagesState pattern.

    Inherits from MessagesState which provides:
    - messages: Annotated[list[BaseMessage], add_messages]

    The add_messages annotation means new messages are appended to the list
    rather than replacing it.

    Additional fields:
    - question: Original user question (for reference in synthesis)
    - retrieved_chunks: Accumulated chunks for citation extraction

    Example:
        >>> initial_state = {
        ...     "messages": [HumanMessage(content="What is deep learning?")],
        ...     "question": "What is deep learning?",
        ...     "retrieved_chunks": [],
        ... }
    """

    # Original user question for reference during synthesis
    question: str

    # Accumulated retrieved chunks for citation extraction after answer generation
    # Format: [{"chunk_id": ..., "doc_name": ..., "content": ..., "similarity": ...}]
    retrieved_chunks: list[dict[str, Any]]


# Type alias for backward compatibility
RAGReActState = RAGAgentState
