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


class RewriteQueryInput(BaseModel):
    """Input schema for query rewrite tool."""

    original_query: str = Field(
        description="The original user question or query that needs optimization"
    )
    context: str = Field(
        default="",
        description="Optional conversation context to inform rewriting (e.g., previous questions/answers)"
    )


class DecomposeQueryInput(BaseModel):
    """Input schema for query decomposition."""

    complex_query: str = Field(
        description="A complex question with multiple parts that should be broken down into simpler sub-queries"
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


def _rewrite_query_impl(
    original_query: str,
    context: str,
    api_key: str,
) -> str:
    """
    Internal implementation for query rewriting.

    Args:
        original_query: The user's original question or query
        context: Optional conversation context to inform rewriting
        api_key: API key for the model (from config)

    Returns:
        Optimized search query string with key terms extracted
    """
    try:
        from langchain.chat_models import init_chat_model

        # Initialize LLM for query rewriting
        # Use gpt-4.1-mini (fast and cheap) for query optimization tasks
        model = init_chat_model(
            model="openai:gpt-4.1-mini",
            api_key=api_key,
            temperature=0.1,  # Lower temperature for consistent rewrites
        )

        # Create rewriting prompt
        rewrite_prompt = f"""Transform the following query into an optimized search query for a knowledge base.

Instructions:
1. Extract key entities, concepts, and technical terms
2. Remove filler words (can, you, tell, me, how, what, please, etc.)
3. Keep important nouns, verbs, and domain-specific terms
4. Add relevant synonyms if helpful
5. Format as a concise keyword-rich phrase (3-8 words)

Original query: "{original_query}"
{f'Context: {context}' if context else ''}

Return ONLY the optimized query, nothing else."""

        # Call LLM
        response = model.invoke(rewrite_prompt)

        # Extract optimized query from response
        optimized_query = response.content.strip().strip('"')

        # Fallback: if response is empty or too similar to original, use original
        if not optimized_query or len(optimized_query) < 2:
            logger.warning(
                f"Query rewrite produced empty result, using original: '{original_query}'"
            )
            return original_query

        logger.info(f"Query rewrite: '{original_query}' → '{optimized_query}'")

        return optimized_query

    except Exception as e:
        logger.exception(f"Error in _rewrite_query_impl: {e}")
        # Fallback to original query on error
        logger.warning(f"Query rewrite failed, using original: '{original_query}'")
        return original_query


@tool(args_schema=RewriteQueryInput)
def rewrite_query_for_retrieval(
    original_query: str,
    context: str = "",
    api_key: str = None,  # Injected via bind()
) -> str:
    """
    Transform a user query into an optimized search query for the knowledge base.

    Use this tool when you have a vague, verbose, or poorly worded question that needs
    optimization before retrieval. The tool extracts key entities, concepts, and technical
    terms while removing filler words.

    This improves retrieval quality by creating focused, keyword-rich queries that match
    better with the semantic search system.

    Args:
        original_query: The user's original question or query
        context: Optional conversation context to inform rewriting (e.g., previous topics discussed)

    Returns:
        Optimized search query string with key terms extracted

    Example:
        Input: "Can you please tell me how the authentication process actually works in the system?"
        Output: "authentication process workflow system architecture"

        Input: "What are some of the main benefits?"
        Context: "Previously discussed: machine learning applications"
        Output: "machine learning benefits advantages"

    When to use:
    - Vague questions: "How does it work?" → extract specific concepts
    - Verbose questions: "Can you tell me..." → remove filler words
    - Questions needing context: "What about performance?" + context → add context terms
    """
    return _rewrite_query_impl(original_query, context, api_key)


def _decompose_query_impl(
    complex_query: str,
    api_key: str,
) -> list[str]:
    """
    Internal implementation for query decomposition.

    Args:
        complex_query: A multi-part or complex question
        api_key: API key for the model (from config)

    Returns:
        List of simpler, focused sub-queries (typically 2-4 queries)
    """
    try:
        from langchain.chat_models import init_chat_model

        # Initialize LLM for decomposition
        # Use gpt-4.1-mini (fast and cheap) for query optimization tasks
        model = init_chat_model(
            model="openai:gpt-4.1-mini",
            api_key=api_key,
            temperature=0.1,  # Lower temperature for consistent decomposition
        )

        # Create decomposition prompt
        decompose_prompt = f"""Analyze the following question and break it down into focused sub-queries if it has multiple parts.

Instructions:
1. Identify distinct aspects, components, or dimensions of the question
2. Create 2-4 focused sub-queries (each covering one aspect)
3. Keep sub-queries concise and searchable (3-6 words each)
4. If the question is already focused (single aspect), return it as-is in a list

Original question: "{complex_query}"

Return ONLY a JSON list of sub-queries, like: ["query 1", "query 2"]
Do not include any explanation, just the JSON list."""

        # Call LLM
        response = model.invoke(decompose_prompt)

        # Parse response as JSON list
        import json

        content = response.content.strip()

        # Extract JSON array from response (handle cases where LLM adds markdown)
        if "```" in content:
            # Extract from code block
            import re

            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

        try:
            sub_queries = json.loads(content)

            # Validate result
            if not isinstance(sub_queries, list) or not sub_queries:
                raise ValueError("Invalid sub-queries format")

            # Ensure all elements are strings
            sub_queries = [str(q).strip() for q in sub_queries if q]

            if not sub_queries:
                raise ValueError("No valid sub-queries extracted")

            logger.info(
                f"Query decomposition: '{complex_query}' → {len(sub_queries)} sub-queries: {sub_queries}"
            )

            return sub_queries

        except (json.JSONDecodeError, ValueError) as parse_error:
            logger.warning(
                f"Failed to parse decomposition response: {parse_error}. "
                f"Response: {content}. Using original query."
            )
            return [complex_query]

    except Exception as e:
        logger.exception(f"Error in _decompose_query_impl: {e}")
        # Fallback to original query on error
        logger.warning(f"Query decomposition failed, using original: '{complex_query}'")
        return [complex_query]


@tool(args_schema=DecomposeQueryInput)
def decompose_query(
    complex_query: str,
    api_key: str = None,  # Injected via bind()
) -> list[str]:
    """
    Break down a complex question into simpler, focused sub-queries.

    Use this tool when a question has multiple parts or aspects that should be researched
    separately for comprehensive coverage. This enables systematic retrieval for each
    component of the question.

    Args:
        complex_query: A multi-part or complex question

    Returns:
        List of simpler, focused sub-queries (typically 2-4 queries)

    Example:
        Input: "What are the advantages and disadvantages of approach X?"
        Output: ["advantages of approach X", "disadvantages of approach X"]

        Input: "Compare the performance and cost of options A and B"
        Output: ["option A performance", "option B performance", "option A cost", "option B cost"]

        Input: "How does authentication work and what are the security implications?"
        Output: ["authentication workflow process", "authentication security implications"]

    When to use:
    - Multi-part questions: "What are X and Y?" → separate queries
    - Comparison questions: "Compare A and B" → query each separately
    - Questions with "and": Often indicates multiple aspects
    - Questions asking for pros/cons, benefits/drawbacks, etc.
    """
    return _decompose_query_impl(complex_query, api_key)
