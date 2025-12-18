"""
Context management for RAG agent request-scoped data.

Provides context variables that allow passing non-serializable objects
(like tool instances) from the server to graph nodes without causing
circular reference issues during state serialization.
"""

from contextvars import ContextVar

# Track retrieval tools for the current request
# These are stored here instead of in the graph config to avoid
# circular reference errors when ag_ui_langgraph tries to serialize the state
current_retrieval_tools: ContextVar[list | None] = ContextVar(
    "current_retrieval_tools", default=None
)
