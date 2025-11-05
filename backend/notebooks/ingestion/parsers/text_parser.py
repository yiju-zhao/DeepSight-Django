"""
Text parser for markdown and plain text files.
"""

import logging
from typing import Any, Optional

from ..exceptions import ParseError
from .base_parser import BaseParser, ParseResult


class TextParser(BaseParser):
    """Text parser for markdown and plain text formats."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    async def parse(self, file_path: str, metadata: dict[str, Any]) -> ParseResult:
        """
        Parse text file based on extension.

        Args:
            file_path: Path to text file (can be None for in-memory content)
            metadata: File metadata including 'content' for in-memory parsing

        Returns:
            ParseResult with extracted content and metadata
        """
        file_extension = metadata.get("file_extension", "").lower()

        # Route to appropriate parser
        if file_extension == ".md":
            return await self._parse_markdown(file_path, metadata)
        elif file_extension == ".txt":
            return await self._parse_plain_text(file_path, metadata)
        else:
            # Generic text handling
            return await self._parse_plain_text(file_path, metadata)

    async def _parse_markdown(
        self, file_path: str, metadata: dict[str, Any]
    ) -> ParseResult:
        """Parse markdown file directly."""
        self.logger.info(f"Processing markdown file: {file_path}")

        # Check if content is provided in metadata (for in-memory parsing)
        if "content" in metadata and metadata["content"]:
            content = metadata["content"]
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

        text_metadata = {
            "word_count": len(content.split()),
            "char_count": len(content),
            "line_count": len(content.splitlines()),
            "encoding": "utf-8",
            "processing_method": "direct_markdown",
            "is_markdown_file": True,
        }

        # Use original filename for markdown files
        original_filename = metadata.get("filename", "document.md")

        return ParseResult(
            content=content,
            metadata=text_metadata,
            features_available=["content_analysis", "summarization"],
        )

    async def _parse_plain_text(
        self, file_path: str, metadata: dict[str, Any]
    ) -> ParseResult:
        """Parse plain text file."""
        self.logger.info(f"Processing text file: {file_path}")

        # Check if content is provided in metadata (for in-memory parsing)
        if "content" in metadata and metadata["content"]:
            content = metadata["content"]
            encoding = "utf-8"
        else:
            # Try different encodings
            content = None
            encoding = None
            for enc in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(file_path, "r", encoding=enc) as f:
                        content = f.read()
                    encoding = enc
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                raise ParseError(
                    "Could not decode text file with any supported encoding"
                )

        text_metadata = {
            "word_count": len(content.split()),
            "char_count": len(content),
            "line_count": len(content.splitlines()),
            "encoding": encoding,
        }

        return ParseResult(
            content=content,
            metadata=text_metadata,
            features_available=["content_analysis", "summarization"],
        )
