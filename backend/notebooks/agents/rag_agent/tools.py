"""
LangChain tools for RAG agent using MCP (Model Context Protocol).

Provides tool wrappers around RAGFlow MCP server following LangGraph
best practices. Uses langchain-mcp-adapters to connect to the RAGFlow
MCP server at http://localhost:9382/mcp/.
"""

import logging
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)


async def create_mcp_retrieval_tools(
    dataset_ids: list[str],
    mcp_server_url: str = "http://localhost:9382/mcp/",
    document_ids: list[str] | None = None,
):
    """
    Factory function to create MCP-based retrieval tools.

    Creates LangChain tools that connect to the RAGFlow MCP server and use
    the ragflow_retrieval tool provided by the server.

    Args:
        dataset_ids: List of dataset IDs to search
        mcp_server_url: URL of the RAGFlow MCP server (default: http://localhost:9382/mcp/)
        document_ids: Optional list of specific document IDs to search within

    Returns:
        List of LangChain tools from the MCP server that can be used with LangGraph agents

    Example:
        >>> tools = await create_mcp_retrieval_tools(
        ...     dataset_ids=["bc4177924a7a11f09eff238aa5c10c94"]
        ... )
        >>> # Use tools with LangGraph agent
        >>> agent = create_agent("claude-sonnet-4-5-20250929", tools)
    """
    logger.info(f"[create_mcp_retrieval_tools] Connecting to MCP server: {mcp_server_url}")
    logger.info(f"[create_mcp_retrieval_tools] Dataset IDs: {dataset_ids}")

    # Normalize IDs to strings to avoid type surprises in MCP payloads
    default_dataset_ids = [str(ds_id) for ds_id in dataset_ids]
    default_document_ids = [str(doc_id) for doc_id in (document_ids or [])]

    # Configure MCP client for RAGFlow server
    client = MultiServerMCPClient(
        {
            "ragflow": {
                "transport": "http",  # HTTP-based remote server
                "url": mcp_server_url,
            }
        }
    )

    try:
        # Get all available tools from the MCP server
        tools = await client.get_tools()
        logger.info(f"[create_mcp_retrieval_tools] Retrieved {len(tools)} tools from MCP server")

        # Store metadata on tools for later use
        def _apply_defaults_to_payload(payload: Any) -> dict[str, Any]:
            """
            Ensure payload always includes dataset/document IDs for notebook scoping.
            """
            if payload is None:
                payload = {}
            if not isinstance(payload, dict):
                # If the model sends a bare question string, wrap it
                payload = {"question": payload}

            # Never mutate caller's dict
            merged = dict(payload)
            merged.setdefault("dataset_ids", default_dataset_ids)
            if default_document_ids:
                merged.setdefault("document_ids", default_document_ids)
            return merged

        for tool in tools:
            # Store default parameters for debugging/inspection
            tool._default_dataset_ids = default_dataset_ids
            tool._default_document_ids = default_document_ids

            # Wrap invoke/ainvoke to inject defaults even if the LLM omits them
            if hasattr(tool, "invoke"):
                original_invoke = tool.invoke

                def invoke_with_defaults(
                    payload,
                    _orig=original_invoke,
                    _apply=_apply_defaults_to_payload,
                ):
                    return _orig(_apply(payload))

                tool.invoke = invoke_with_defaults  # type: ignore[attr-defined]

            if hasattr(tool, "ainvoke"):
                original_ainvoke = tool.ainvoke

                async def ainvoke_with_defaults(
                    payload,
                    _orig=original_ainvoke,
                    _apply=_apply_defaults_to_payload,
                ):
                    return await _orig(_apply(payload))

                tool.ainvoke = ainvoke_with_defaults  # type: ignore[attr-defined]

        return tools

    except Exception as e:
        logger.error(f"[create_mcp_retrieval_tools] Failed to connect to MCP server: {e}")
        raise


async def invoke_mcp_retrieval(
    tools: list[Any],
    question: str,
    dataset_ids: list[str] | None = None,
    document_ids: list[str] | None = None,
) -> str:
    """
    Invoke the RAGFlow retrieval tool from the MCP server.

    This is a helper function that wraps the MCP tool invocation with proper
    parameter formatting and error handling.

    Args:
        tools: List of tools returned from create_mcp_retrieval_tools
        question: The search query to find relevant documents
        dataset_ids: Optional override for dataset IDs (uses default from create_mcp_retrieval_tools if None)
        document_ids: Optional override for document IDs (uses default from create_mcp_retrieval_tools if None)

    Returns:
        Formatted string with relevant document chunks and their sources.

    Example:
        >>> tools = await create_mcp_retrieval_tools(dataset_ids=["dataset_123"])
        >>> result = await invoke_mcp_retrieval(
        ...     tools=tools,
        ...     question="How to install neovim?"
        ... )
    """
    logger.info(f"[invoke_mcp_retrieval] Query: {question[:100]}...")

    # Find the ragflow_retrieval tool
    retrieval_tool = None
    for tool in tools:
        if hasattr(tool, "name") and tool.name == "ragflow_retrieval":
            retrieval_tool = tool
            break

    if retrieval_tool is None:
        logger.error("[invoke_mcp_retrieval] ragflow_retrieval tool not found")
        raise ValueError("ragflow_retrieval tool not found in MCP server tools")

    # Use provided dataset_ids or fall back to defaults
    final_dataset_ids = dataset_ids or getattr(retrieval_tool, "_default_dataset_ids", [])
    final_document_ids = document_ids or getattr(retrieval_tool, "_default_document_ids", [])

    try:
        # Invoke the MCP tool with proper arguments
        response = await retrieval_tool.ainvoke(
            {
                "dataset_ids": final_dataset_ids,
                "document_ids": final_document_ids,
                "question": question,
            }
        )

        logger.info(f"[invoke_mcp_retrieval] Response type: {type(response)}")

        # Parse and format the response
        # The MCP server returns a ModelDump with content
        if hasattr(response, "content") and isinstance(response.content, list):
            # Extract text from content blocks
            formatted_chunks = []
            for content_block in response.content:
                if hasattr(content_block, "text"):
                    formatted_chunks.append(content_block.text)
            result = "\n\n".join(formatted_chunks)
        elif isinstance(response, str):
            result = response
        else:
            # Fallback: convert to string
            result = str(response)

        logger.info(f"[invoke_mcp_retrieval] Retrieved {len(result)} characters")
        return result

    except Exception as e:
        logger.error(f"[invoke_mcp_retrieval] Retrieval error: {e}")
        return f"Error retrieving documents: {str(e)}"
