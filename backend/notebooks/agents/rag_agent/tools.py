"""
LangChain tools for RAG agent.

Defines the retrieve_knowledge tool for accessing the knowledge base.
"""

import logging
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RetrieveKnowledgeInput(BaseModel):
    """Input schema for retrieve_knowledge tool."""

    query: str = Field(
        description="Specific, focused question to search the knowledge base. "
        "Be precise - good queries get better results. "
        "Example: 'What are the main features of Python asyncio?' "
        "rather than 'Tell me about Python'"
    )
    top_k: int = Field(
        default=6, ge=1, le=30, description="Number of relevant passages to retrieve (1-30)"
    )


def _retrieve_knowledge_impl(
    query: str,
    top_k: int,
    retrieval_service,
    dataset_ids: Optional[list[str]],
) -> str:
    """
    Internal implementation for knowledge retrieval.

    This function contains the actual logic for retrieving information from the knowledge base.
    It is called by both the tool wrapper and the closure in graph.py.

    Args:
        query: Specific search query
        top_k: Number of passages to retrieve
        retrieval_service: RetrievalService instance
        dataset_ids: List of dataset IDs to search

    Returns:
        Formatted string with relevant passages, sources, and similarity scores.
    """
    if not retrieval_service:
        logger.error("retrieve_knowledge called without retrieval_service")
        return "Error: Retrieval service not configured."

    if not dataset_ids:
        logger.error("retrieve_knowledge called without dataset_ids")
        return "Error: No datasets configured for search."

    try:
        logger.info(f"Retrieving knowledge: query='{query[:100]}...', top_k={top_k}")

        # Call retrieval service
        result = retrieval_service.retrieve_chunks(
            question=query, dataset_ids=dataset_ids, top_k=min(top_k, 30)
        )

        if not result.chunks:
            return "No relevant information found in the knowledge base for this query."

        # Format chunks for agent
        formatted = retrieval_service.format_chunks_for_agent(
            result.chunks, max_chunks=top_k
        )

        logger.info(
            f"Retrieved {len(result.chunks)} chunks for query: '{query[:50]}...'"
        )

        return formatted

    except Exception as e:
        logger.exception(f"Error in retrieve_knowledge: {e}")
        return f"Error retrieving information: {str(e)}"


@tool(args_schema=RetrieveKnowledgeInput)
def retrieve_knowledge(
    query: str,
    top_k: int = 6,
    retrieval_service=None,  # Injected via bind()
    dataset_ids: Optional[list[str]] = None,  # Injected via bind()
) -> str:
    """
    Retrieve relevant information from the knowledge base.

    This is your only way to access factual information from the documents.
    Use it when you need specific information to answer the user's question.

    The tool searches through the notebook's documents and returns relevant passages
    with their source documents and similarity scores.

    Args:
        query: Specific search query (be precise for better results)
        top_k: Number of passages to retrieve (default: 6)

    Returns:
        Formatted string with relevant passages, sources, and similarity scores.
        If no relevant information is found, returns a message indicating this.

    Example:
        To find information about a specific topic:
        retrieve_knowledge(query="What is the capital of France?", top_k=3)

        Returns:
        ```
        Found 3 relevant passages:

        [1] Geography Guide.pdf
        France is a country in Western Europe. Its capital and largest city is Paris...
        Similarity: 0.95

        [2] European Capitals.pdf
        Paris, the capital of France, is located in the north-central part of the country...
        Similarity: 0.89
        ...
        ```
    """
    return _retrieve_knowledge_impl(query, top_k, retrieval_service, dataset_ids)
