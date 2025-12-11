"""
LangChain tools for RAG agent.

Provides tool wrappers around RAGFlow retrieval service following LangGraph
best practices. Tools use the @tool decorator and proper docstrings for
automatic schema generation.
"""

import logging
from typing import Any

from langchain.tools import tool

logger = logging.getLogger(__name__)


def create_retrieval_tool(
    ragflow_service: Any,
    dataset_ids: list[str],
    similarity_threshold: float = 0.4,
    top_k: int = 10,
):
    """
    Factory function to create a retrieval tool with injected dependencies.

    Creates a LangChain @tool decorated function that wraps the RAGFlow
    retrieval service. The tool is configured with the provided dataset IDs
    and retrieval parameters.

    Args:
        ragflow_service: RagflowService or RagflowChunkService instance
        dataset_ids: List of dataset IDs to search
        similarity_threshold: Minimum similarity for chunk inclusion (default: 0.4)
        top_k: Maximum chunks to retrieve per query (default: 10)

    Returns:
        A LangChain @tool decorated function that performs retrieval

    Example:
        >>> from infrastructure.ragflow.service import RagflowService
        >>> ragflow = RagflowService()
        >>> retriever = create_retrieval_tool(ragflow, ["dataset_123"])
        >>> result = retriever.invoke({"query": "What is deep learning?"})
    """

    @tool
    def retrieve_documents(query: str) -> str:
        """Search and return relevant documents from the knowledge base.

        Use this tool when you need information from the knowledge base to answer
        user questions. The tool performs semantic search and returns the most
        relevant document chunks with their source information.

        Args:
            query: The search query to find relevant documents. Use specific
                   keywords and clear phrasing for best results.

        Returns:
            Formatted string with relevant document chunks and their sources.
            Returns "No relevant documents found." if no matches above threshold.
        """
        logger.info(f"[retrieve_documents] Query: {query[:100]}...")

        try:
            # Call RAGFlow retrieval service
            result = ragflow_service.retrieve_chunks(
                question=query,
                dataset_ids=dataset_ids,
                similarity_threshold=similarity_threshold,
                top_k=top_k,
            )

            # Handle empty results
            chunks = getattr(result, "chunks", [])
            if not chunks:
                logger.info("[retrieve_documents] No relevant chunks found")
                return "No relevant documents found."

            logger.info(f"[retrieve_documents] Found {len(chunks)} relevant chunks")

            # Format chunks for LLM consumption
            formatted_chunks = []
            for i, chunk in enumerate(chunks, 1):
                doc_name = getattr(chunk, "document_name", "Unknown Document")
                content = getattr(chunk, "content", "")
                similarity = getattr(chunk, "similarity", 0.0)

                # Format each chunk with clear structure
                formatted_chunks.append(
                    f"[{i}] {doc_name} (relevance: {similarity:.2f})\n{content}"
                )

            return "\n\n".join(formatted_chunks)

        except Exception as e:
            logger.error(f"[retrieve_documents] Retrieval error: {e}")
            return f"Error retrieving documents: {str(e)}"

    # Store metadata for citations extraction
    retrieve_documents._dataset_ids = dataset_ids
    retrieve_documents._ragflow_service = ragflow_service

    return retrieve_documents
