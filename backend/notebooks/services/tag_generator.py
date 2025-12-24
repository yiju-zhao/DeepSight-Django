"""
Tag Generator Service

Uses LLM to generate relevant tags for note content.
"""

import logging
from functools import lru_cache
from typing import List

from langchain.chat_models import init_chat_model

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_openai_api_key() -> str:
    """Get OpenAI API key from Django settings."""
    from django.conf import settings
    return getattr(settings, "OPENAI_API_KEY", "")


class TagGeneratorService:
    """Service for generating tags from content using LLM."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        """Lazy initialization of the LLM model."""
        if self._model is None:
            api_key = _get_openai_api_key()
            if not api_key:
                logger.warning("OpenAI API key not configured, tag generation disabled")
                return None

            self._model = init_chat_model(
                model="openai:gpt-4o-mini",
                api_key=api_key,
                temperature=0.3,
            )
        return self._model

    def generate_tags(self, content: str, max_tags: int = 3) -> List[str]:
        """
        Generate relevant tags for the given content.

        Args:
            content: The note content to analyze
            max_tags: Maximum number of tags to generate (default: 3)

        Returns:
            List of generated tags, or empty list if generation fails
        """
        model = self._get_model()
        if model is None:
            return []

        # Limit content to avoid token limits
        truncated_content = content[:1500] if len(content) > 1500 else content

        prompt = f"""Analyze the following content and generate exactly {max_tags} short, relevant tags.

Rules:
- Each tag should be 1-2 words maximum
- Tags should be lowercase with hyphens for multi-word tags (e.g., "data-analysis")
- Tags should capture the main topics, themes, or concepts
- Return ONLY the tags, separated by commas, nothing else

Content:
{truncated_content}

Tags:"""

        try:
            response = model.invoke(prompt)
            raw_tags = response.content.strip()

            # Parse and clean tags
            tags = []
            for tag in raw_tags.split(","):
                cleaned = tag.strip().lower().replace(" ", "-")
                # Remove any quotes or extra characters
                cleaned = cleaned.strip("\"'")
                if cleaned and len(cleaned) <= 30:
                    tags.append(cleaned)

            return tags[:max_tags]

        except Exception as e:
            logger.error(f"Tag generation failed: {e}")
            return []


# Singleton instance
_tag_generator = None


def get_tag_generator() -> TagGeneratorService:
    """Get the singleton TagGeneratorService instance."""
    global _tag_generator
    if _tag_generator is None:
        _tag_generator = TagGeneratorService()
    return _tag_generator


def generate_tags_for_content(content: str, max_tags: int = 3) -> List[str]:
    """
    Convenience function to generate tags for content.

    Args:
        content: The content to analyze
        max_tags: Maximum number of tags to generate

    Returns:
        List of generated tags
    """
    return get_tag_generator().generate_tags(content, max_tags)
