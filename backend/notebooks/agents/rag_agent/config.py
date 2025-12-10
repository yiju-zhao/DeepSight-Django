"""
Configuration for RAG agent.

Defines parameters for model selection, iteration limits,
and retrieval settings.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RAGAgentConfig:
    """
    Configuration for RAG agent execution.

    Attributes:
        model_name: OpenAI model name (e.g., "gpt-4.1-mini", "gpt-4-turbo")
        api_key: OpenAI API key
        temperature: Sampling temperature (0.0-1.0), lower is more deterministic
        max_iterations: Maximum agent loop iterations (hard limit)
        retrieval_service: RetrievalService instance for knowledge access
        dataset_ids: List of RAGFlow dataset IDs to search
        similarity_threshold: Minimum similarity for retrieval (0.0-1.0)
        top_k: Number of chunks to retrieve per query
    """

    # Model configuration
    model_name: str = "gpt-4.1-mini"
    api_key: Optional[str] = None
    temperature: float = 0.3

    # Agent behavior
    max_iterations: int = 5

    # Retrieval configuration
    retrieval_service: Optional[object] = None
    dataset_ids: list[str] = field(default_factory=list)
    similarity_threshold: float = 0.2
    top_k: int = 6

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.temperature < 0.0 or self.temperature > 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0")

        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

        if self.similarity_threshold < 0.0 or self.similarity_threshold > 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")

        if self.top_k < 1:
            raise ValueError("top_k must be at least 1")

        # Warn if retrieval service is provided but no datasets configured
        if self.retrieval_service is not None and not self.dataset_ids:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "RAGAgentConfig: retrieval_service is configured but dataset_ids is empty. "
                "The agent will not be able to retrieve information from the knowledge base."
            )
