"""
Ingestion module exceptions.
"""


class IngestionError(Exception):
    """Base exception for ingestion module."""

    pass


class SourceError(IngestionError):
    """URL/download failed."""

    pass


class ParseError(IngestionError):
    """Parsing failed."""

    pass


class TranscriptionError(IngestionError):
    """Transcription failed."""

    pass


class StorageError(IngestionError):
    """Storage failed."""

    pass
