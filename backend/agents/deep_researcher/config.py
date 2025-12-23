"""
Configuration for Deep Researcher Agent

This module bridges Django settings for the research agent,
providing access to API keys and model configurations.
"""

from datetime import datetime
from typing import Optional

from django.conf import settings


def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.now().strftime("%B %d, %Y")


def get_tavily_api_key() -> str:
    """Get Tavily API key from Django settings."""
    return getattr(settings, "TAVILY_API_KEY", "")


def get_openai_api_key() -> str:
    """Get OpenAI API key from Django settings."""
    return getattr(settings, "OPENAI_API_KEY", "")


def get_model_config() -> dict:
    """Get model configuration for research agent."""
    return {
        "model": getattr(settings, "RESEARCH_MODEL", "gpt-4.1"),
        "api_key": get_openai_api_key(),
        "temperature": getattr(settings, "RESEARCH_TEMPERATURE", 0.7),
        "top_p": getattr(settings, "RESEARCH_TOP_P", 0.95),
    }


def get_compression_model_config() -> dict:
    """Get model configuration for research compression."""
    return {
        "model": getattr(settings, "COMPRESSION_MODEL", "gpt-4.1"),
        "api_key": get_openai_api_key(),
        "max_tokens": getattr(settings, "COMPRESSION_MAX_TOKENS", 32000),
    }


class ResearchConfig:
    """Configuration settings for research agent."""

    # Maximum concurrent research workers
    MAX_CONCURRENT_RESEARCHERS: int = 3

    # Maximum research iterations before stopping
    MAX_RESEARCHER_ITERATIONS: int = 10

    # Maximum context length for summarization
    MAX_CONTEXT_LENGTH: int = 250000

    # Default search parameters
    DEFAULT_SEARCH_MAX_RESULTS: int = 3
    DEFAULT_SEARCH_TOPIC: str = "general"

    # Timeout settings (in seconds)
    DEFAULT_TIMEOUT: float = 300.0
    SEARCH_TIMEOUT: float = 30.0

    @classmethod
    def from_settings(cls) -> "ResearchConfig":
        """Create config from Django settings with overrides."""
        config = cls()
        config.MAX_CONCURRENT_RESEARCHERS = getattr(
            settings, "RESEARCH_MAX_CONCURRENT", cls.MAX_CONCURRENT_RESEARCHERS
        )
        config.MAX_RESEARCHER_ITERATIONS = getattr(
            settings, "RESEARCH_MAX_ITERATIONS", cls.MAX_RESEARCHER_ITERATIONS
        )
        config.DEFAULT_TIMEOUT = getattr(
            settings, "RESEARCH_TIMEOUT", cls.DEFAULT_TIMEOUT
        )
        return config
