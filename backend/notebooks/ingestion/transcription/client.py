"""
Minimal transcription client interface.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional


class TranscriptionClient(ABC):
    """Abstract transcription client."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    @abstractmethod
    async def transcribe(self, file_path: str) -> str:
        """
        Transcribe audio/video file.

        Args:
            file_path: Path to audio/video file

        Returns:
            Transcribed text

        Raises:
            TranscriptionError: If transcription fails
        """
        pass
