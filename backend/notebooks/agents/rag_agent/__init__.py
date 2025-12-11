"""
RAG Agent for multi-round knowledge retrieval and synthesis.

Provides agentic RAG capabilities using LangGraph for orchestration
and RAGFlow MCP server for knowledge retrieval. Follows LangGraph best practices
with tool-based retrieval and automated routing.

Uses RAGFlow MCP server via langchain-mcp-adapters for standardized retrieval.

Usage:
    from notebooks.agents.rag_agent import create_rag_agent, RAGAgentConfig
    from langchain_core.messages import HumanMessage

    config = RAGAgentConfig(
        model_name="gpt-4o-mini",
        dataset_ids=["dataset_id"],
        mcp_server_url="http://localhost:9382/mcp/",
    )
    agent = await create_rag_agent(config)

    result = await agent.ainvoke({
        "messages": [HumanMessage(content="What is deep learning?")],
        "question": "What is deep learning?",
        "retrieved_chunks": [],
    })
"""

from .graph import create_rag_agent
from .config import RAGAgentConfig
from .states import RAGAgentState
from .tools import create_mcp_retrieval_tools, invoke_mcp_retrieval

__all__ = [
    "create_rag_agent",
    "RAGAgentConfig",
    "RAGAgentState",
    "create_mcp_retrieval_tools",
    "invoke_mcp_retrieval",
]
