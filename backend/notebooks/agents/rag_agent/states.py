"""
LangGraph state definitions for RAG agent.

Defines the state structure that flows through the agent graph,
including messages, iteration tracking, and retrieval history.
"""

from typing import Annotated, Sequence
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class RAGAgentState(TypedDict):
    """
    State for the RAG agent workflow.

    This state flows through the LangGraph nodes and tracks:
    - Conversation messages (with tool calls and responses)
    - Iteration count (to enforce max iterations)
    - Retrieval history (for logging and debugging)
    - Finish flag (to signal completion)
    """

    # Message history with automatic merging of new messages
    # add_messages reducer handles appending and updating messages
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Iteration counter to enforce max_iterations limit
    iteration_count: int

    # Track retrieval queries for logging/debugging
    # List of query strings passed to retrieve_knowledge tool
    retrieval_history: list[str]

    # Explicit finish signal
    # Set to True when agent should stop iterating
    should_finish: bool
