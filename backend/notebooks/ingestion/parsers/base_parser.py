"""
Base parser interface and common types for ingestion module.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal, Optional


@dataclass
class ParseResult:
    """Unified parsing result."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    features_available: list[str] = field(default_factory=list)
    marker_extraction_result: Optional[dict[str, Any]] = None  # For MinerU PDF results


class BaseParser(ABC):
    """Abstract base parser."""

    @abstractmethod
    async def parse(self, file_path: str, metadata: dict[str, Any]) -> ParseResult:
        """
        Parse file and return unified result.

        Args:
            file_path: Path to the file to parse
            metadata: File metadata (filename, extension, size, etc.)

        Returns:
            ParseResult with content, metadata, and features
        """
        pass
