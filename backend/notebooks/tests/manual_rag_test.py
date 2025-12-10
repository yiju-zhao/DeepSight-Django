"""
Manual testing script for RAG agent improvements.

This script tests the enhanced RAG agent with query optimization tools.
Run this manually to validate improvements in query quality and answer synthesis.

Usage:
    python backend/notebooks/tests/manual_rag_test.py

Requirements:
    - RagFlow service running and configured
    - Valid dataset_ids
    - OpenAI API key configured
"""

import asyncio
import logging
import os
from datetime import datetime

from langchain_core.messages import HumanMessage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Test questions covering different complexity levels
TEST_QUESTIONS = [
    # Simple queries
    {
        "category": "Simple",
        "question": "What are the main features of the product?",
        "expected_behavior": "Should retrieve directly without decomposition",
    },
    {
        "category": "Simple",
        "question": "What is the system architecture?",
        "expected_behavior": "Should retrieve with possible query rewriting",
    },
    # Multi-part queries
    {
        "category": "Multi-part",
        "question": "Compare the performance and cost of options A and B",
        "expected_behavior": "Should decompose into 4 queries (A perf, B perf, A cost, B cost)",
    },
    {
        "category": "Multi-part",
        "question": "What are the benefits and drawbacks of approach X?",
        "expected_behavior": "Should decompose into 2 queries (benefits, drawbacks)",
    },
    # Vague queries
    {
        "category": "Vague",
        "question": "How does it work?",
        "expected_behavior": "Should use query rewriting to add context",
    },
    {
        "category": "Vague",
        "question": "Tell me about the authentication system",
        "expected_behavior": "Should rewrite to focus on authentication architecture",
    },
    # Complex queries
    {
        "category": "Complex",
        "question": "What security measures are implemented and how do they affect performance?",
        "expected_behavior": "Should decompose into security + performance queries",
    },
    {
        "category": "Complex",
        "question": "Explain the data flow from user input to database storage",
        "expected_behavior": "Should retrieve data flow architecture information",
    },
]


async def test_rag_agent():
    """
    Run manual tests on the RAG agent with enhanced prompts and query tools.

    This function:
    1. Initializes the RAG agent with test configuration
    2. Runs all test questions
    3. Prints detailed results for manual evaluation
    4. Logs tool usage patterns
    """
    print("=" * 80)
    print("RAG AGENT MANUAL TEST SUITE")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total test questions: {len(TEST_QUESTIONS)}")
    print("=" * 80)
    print()

    # Import after logging setup
    from notebooks.agents.rag_agent.graph import create_rag_agent
    from notebooks.agents.rag_agent.config import RAGAgentConfig
    from notebooks.services.retrieval_service import RetrievalService
    from infrastructure.ragflow.service import RagflowService

    # Initialize services (requires environment variables)
    try:
        # Get environment variables
        openai_api_key = os.getenv("OPENAI_API_KEY")
        ragflow_api_key = os.getenv("RAGFLOW_API_KEY")
        ragflow_base_url = os.getenv("RAGFLOW_BASE_URL", "http://localhost:9380")

        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        if not ragflow_api_key:
            raise ValueError("RAGFLOW_API_KEY environment variable not set")

        # Initialize RagFlow service
        ragflow_service = RagflowService(
            api_key=ragflow_api_key,
            base_url=ragflow_base_url,
        )

        # Initialize retrieval service
        retrieval_service = RetrievalService(ragflow_service)

        # Get dataset IDs (you'll need to configure this)
        # For testing, you can hardcode or get from environment
        dataset_ids = os.getenv("TEST_DATASET_IDS", "").split(",")
        if not dataset_ids or not dataset_ids[0]:
            print("WARNING: No TEST_DATASET_IDS configured. Using empty list.")
            print("Set TEST_DATASET_IDS environment variable with comma-separated dataset IDs")
            dataset_ids = []

        # Create RAG agent config
        config = RAGAgentConfig(
            model_name="gpt-4.1-mini",
            api_key=openai_api_key,
            retrieval_service=retrieval_service,
            dataset_ids=dataset_ids,
            max_iterations=5,
            temperature=0.3,
        )

        # Create agent
        agent = create_rag_agent(config)

        print(f"✓ Agent initialized successfully")
        print(f"  Model: {config.model_name}")
        print(f"  Max iterations: {config.max_iterations}")
        print(f"  Dataset IDs: {dataset_ids}")
        print()

    except Exception as e:
        logger.exception("Failed to initialize RAG agent")
        print(f"✗ Agent initialization failed: {e}")
        print("\nPlease ensure:")
        print("  1. OPENAI_API_KEY is set")
        print("  2. RAGFLOW_API_KEY is set")
        print("  3. RagFlow service is running")
        print("  4. TEST_DATASET_IDS is configured (optional)")
        return

    # Run tests
    results = []
    for i, test_case in enumerate(TEST_QUESTIONS, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}/{len(TEST_QUESTIONS)}: {test_case['category']}")
        print(f"{'=' * 80}")
        print(f"Question: {test_case['question']}")
        print(f"Expected: {test_case['expected_behavior']}")
        print(f"{'-' * 80}")

        try:
            # Invoke agent
            initial_state = {
                "messages": [HumanMessage(content=test_case["question"])],
                "iteration_count": 0,
                "retrieval_history": [],
                "should_finish": False,
            }

            result = await agent.ainvoke(initial_state)

            # Extract results
            iterations_used = result.get("iteration_count", 0)
            messages = result.get("messages", [])
            final_answer = messages[-1].content if messages else "No answer generated"

            # Count tool calls
            tool_calls_count = sum(
                1
                for msg in messages
                if hasattr(msg, "tool_calls") and msg.tool_calls
            )

            # Log result
            print(f"\n✓ Test completed successfully")
            print(f"  Iterations used: {iterations_used}/{config.max_iterations}")
            print(f"  Tool calls: {tool_calls_count}")
            print(f"\n  Final Answer:")
            print(f"  {'-' * 76}")
            # Truncate answer for readability
            answer_preview = (
                final_answer[:500] + "..."
                if len(final_answer) > 500
                else final_answer
            )
            print(f"  {answer_preview}")
            print(f"  {'-' * 76}")

            # Store result
            results.append(
                {
                    "category": test_case["category"],
                    "question": test_case["question"],
                    "iterations": iterations_used,
                    "tool_calls": tool_calls_count,
                    "answer_length": len(final_answer),
                    "success": True,
                }
            )

        except Exception as e:
            logger.exception(f"Test {i} failed")
            print(f"\n✗ Test failed: {e}")
            results.append(
                {
                    "category": test_case["category"],
                    "question": test_case["question"],
                    "iterations": 0,
                    "tool_calls": 0,
                    "answer_length": 0,
                    "success": False,
                    "error": str(e),
                }
            )

    # Print summary
    print(f"\n\n{'=' * 80}")
    print("TEST SUMMARY")
    print(f"{'=' * 80}")

    total_tests = len(results)
    successful_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - successful_tests

    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {successful_tests / total_tests * 100:.1f}%")

    if successful_tests > 0:
        avg_iterations = sum(r["iterations"] for r in results if r["success"]) / successful_tests
        avg_tool_calls = sum(r["tool_calls"] for r in results if r["success"]) / successful_tests

        print(f"\nAverage iterations: {avg_iterations:.1f}")
        print(f"Average tool calls: {avg_tool_calls:.1f}")

    # Print by category
    print(f"\n{'-' * 80}")
    print("Results by Category:")
    print(f"{'-' * 80}")

    for category in ["Simple", "Multi-part", "Vague", "Complex"]:
        category_results = [r for r in results if r["category"] == category]
        if category_results:
            category_success = sum(1 for r in category_results if r["success"])
            print(f"  {category}: {category_success}/{len(category_results)} passed")

    print(f"\n{'=' * 80}")
    print("Test completed!")
    print(f"{'=' * 80}")


def main():
    """Run the test suite."""
    asyncio.run(test_rag_agent())


if __name__ == "__main__":
    main()
