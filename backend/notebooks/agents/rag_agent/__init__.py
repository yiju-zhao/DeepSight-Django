"""
RAG Agent for multi-round knowledge retrieval and synthesis.

Provides agentic RAG capabilities using LangGraph for orchestration
and RAGFlow for knowledge retrieval. Follows LangGraph best practices
with tool-based retrieval and automated routing.

Usage:
    from notebooks.agents.rag_agent import create_rag_agent, RAGAgentConfig

    config = RAGAgentConfig(
        model_name="gpt-4o-mini",
        retrieval_service=ragflow_service,
        dataset_ids=["dataset_id"],
    )
    agent = create_rag_agent(config)

    result = await agent.ainvoke({
        "messages": [HumanMessage(content="What is deep learning?")],
        "question": "What is deep learning?",
        "retrieved_chunks": [],
    })
"""

from .graph import create_rag_agent
from .config import RAGAgentConfig
from .states import RAGAgentState
from .tools import create_retrieval_tool

__all__ = [
    "create_rag_agent",
    "RAGAgentConfig",
    "RAGAgentState",
    "create_retrieval_tool",
]
