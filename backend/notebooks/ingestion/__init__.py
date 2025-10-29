"""
Ingestion module - Unified file and URL ingestion pipeline.
"""

from .exceptions import (
    IngestionError,
    ParseError,
    SourceError,
    StorageError,
    TranscriptionError,
)
from .orchestrator import IngestionOrchestrator, IngestionResult
from .parsers import (
    BaseParser,
    MediaParser,
    ParseResult,
    PdfParser,
    TextParser,
)
from .transcription import TranscriptionClient, XinferenceProvider
from .url_fetcher import UrlFetchResult, UrlFetcher

__all__ = [
    # Exceptions
    "IngestionError",
    "SourceError",
    "ParseError",
    "TranscriptionError",
    "StorageError",
    # Orchestrator
    "IngestionOrchestrator",
    "IngestionResult",
    # Parsers
    "BaseParser",
    "ParseResult",
    "PdfParser",
    "MediaParser",
    "TextParser",
    # Transcription
    "TranscriptionClient",
    "XinferenceProvider",
    # URL Fetcher
    "UrlFetcher",
    "UrlFetchResult",
]
