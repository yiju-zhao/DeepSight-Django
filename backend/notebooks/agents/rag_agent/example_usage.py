"""
Example usage of RAG Agent with MCP (Model Context Protocol) integration.

This script demonstrates how to use the RAG agent with the RAGFlow MCP server.

Prerequisites:
1. RAGFlow MCP server running at http://localhost:9382/mcp/
2. langchain-mcp-adapters installed (pip install langchain-mcp-adapters)
3. Dataset IDs configured in RAGFlow

Usage:
    python -m notebooks.agents.rag_agent.example_usage
"""

import asyncio
import logging
import os

from langchain_core.messages import HumanMessage

from notebooks.agents.rag_agent import create_rag_agent, RAGAgentConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """
    Main function to demonstrate MCP-based RAG agent usage.
    """
    # Configuration
    dataset_ids = ["bc4177924a7a11f09eff238aa5c10c94"]  # Replace with your dataset IDs
    mcp_server_url = "http://localhost:9382/mcp/"
    model_name = "gpt-4o-mini"
    api_key = os.getenv("OPENAI_API_KEY")

    logger.info("=" * 80)
    logger.info("RAG Agent with MCP Integration - Example Usage")
    logger.info("=" * 80)

    # Create RAG agent configuration
    config = RAGAgentConfig(
        model_name=model_name,
        api_key=api_key,
        dataset_ids=dataset_ids,
        mcp_server_url=mcp_server_url,
        temperature=0.7,
        eval_temperature=0.1,
        synthesis_temperature=0.3,
        similarity_threshold=0.4,
        top_k=10,
    )

    logger.info(f"Configuration:")
    logger.info(f"  - Model: {model_name}")
    logger.info(f"  - Dataset IDs: {dataset_ids}")
    logger.info(f"  - MCP Server: {mcp_server_url}")
    logger.info("")

    # Create the RAG agent
    try:
        logger.info("Creating RAG agent...")
        agent = await create_rag_agent(config)
        logger.info("✓ RAG agent created successfully")
        logger.info("")
    except Exception as e:
        logger.error(f"✗ Failed to create RAG agent: {e}")
        return

    # Example questions to ask
    questions = [
        "How to install neovim?",
        "What are the key features of the system?",
        "Explain the architecture in detail.",
    ]

    # Test each question
    for i, question in enumerate(questions, 1):
        logger.info(f"Question {i}/{len(questions)}: {question}")
        logger.info("-" * 80)

        try:
            # Invoke the agent
            result = await agent.ainvoke({
                "messages": [HumanMessage(content=question)],
                "question": question,
                "retrieved_chunks": [],
            })

            # Extract the final answer
            final_messages = result.get("messages", [])
            if final_messages:
                final_answer = final_messages[-1].content
                logger.info(f"Answer:\n{final_answer}")
            else:
                logger.warning("No answer generated")

        except Exception as e:
            logger.error(f"✗ Error processing question: {e}")

        logger.info("")

    logger.info("=" * 80)
    logger.info("Example completed")
    logger.info("=" * 80)


async def test_direct_mcp_tool():
    """
    Test the MCP retrieval tool directly without the agent.

    This is useful for debugging MCP server connectivity.
    """
    from notebooks.agents.rag_agent import create_mcp_retrieval_tools, invoke_mcp_retrieval

    logger.info("=" * 80)
    logger.info("Testing Direct MCP Tool Invocation")
    logger.info("=" * 80)

    dataset_ids = ["bc4177924a7a11f09eff238aa5c10c94"]
    mcp_server_url = "http://localhost:9382/mcp/"

    try:
        # Create MCP tools
        logger.info(f"Connecting to MCP server: {mcp_server_url}")
        tools = await create_mcp_retrieval_tools(
            dataset_ids=dataset_ids,
            mcp_server_url=mcp_server_url,
        )
        logger.info(f"✓ Retrieved {len(tools)} tools from MCP server")

        for tool in tools:
            logger.info(f"  - Tool: {tool.name}")

        # Test retrieval
        question = "How to install neovim?"
        logger.info(f"\nTesting retrieval with question: {question}")

        result = await invoke_mcp_retrieval(
            tools=tools,
            question=question,
            dataset_ids=dataset_ids,
        )

        logger.info(f"\nRetrieval result:\n{result[:500]}...")  # First 500 chars

    except Exception as e:
        logger.error(f"✗ Error testing MCP tool: {e}")
        import traceback
        traceback.print_exc()

    logger.info("")


if __name__ == "__main__":
    # Choose which example to run:
    # 1. Full agent example (default)
    # 2. Direct MCP tool test (uncomment below)

    asyncio.run(main())

    # Or test direct MCP tool:
    # asyncio.run(test_direct_mcp_tool())
