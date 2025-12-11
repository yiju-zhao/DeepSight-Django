"""
LangGraph state definitions for RAG agent.

Defines the state structure that flows through the agent graph,
supporting ReAct (Reasoning + Acting) pattern with iterative retrieval.
"""

from typing import Any
from typing_extensions import TypedDict


class RAGReActState(TypedDict):
    """
    State for the ReAct RAG agent workflow.

    This state supports the ReAct pattern:
    - REASON: Agent thinks and generates queries
    - ACT: Execute retrieval based on queries
    - EVALUATE: LLM assesses retrieval results and extracts relevant info
    - OBSERVE: Add results to history and continue reasoning

    Flow through nodes:
    reasoning → retrieval → evaluation → (continue reasoning OR synthesize answer)
    """

    # ===== Core Question =====
    # Original user question
    question: str

    # ===== ReAct Loop State =====
    # Message history for LLM context (role + content dicts)
    # Format: [{"role": "user"/"assistant", "content": "..."}]
    message_history: list[dict[str, str]]

    # All reasoning steps (includes queries and search results)
    # Used for history truncation and context management
    reasoning_steps: list[str]

    # Current iteration number (0-indexed)
    iteration: int

    # ===== Query Management =====
    # All executed queries (for deduplication)
    executed_queries: list[str]

    # Current reasoning output from reasoning_node
    current_reasoning: str

    # Current queries extracted from reasoning
    current_queries: list[str]

    # ===== Retrieval Results =====
    # Current batch of retrieved chunks
    current_retrieved: list[dict[str, Any]]

    # All accumulated chunks (for final citations)
    retrieved_chunks: list[dict[str, Any]]

    # ===== Final Output =====
    # Final synthesized answer
    final_answer: str

    # Control flag (for conditional edges)
    should_continue: bool
