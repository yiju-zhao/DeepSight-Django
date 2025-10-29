"""
Xinference transcription provider.
"""

import asyncio
import logging
from typing import Optional

from ...exceptions import TranscriptionError
from ..client import TranscriptionClient


class XinferenceProvider(TranscriptionClient):
    """Xinference transcription implementation."""

    def __init__(
        self,
        xinference_url: str = "http://localhost:9997",
        model_uid: str = "Bella-whisper-large-v3-zh",
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(logger)
        self.xinference_url = xinference_url
        self.model_uid = model_uid

    async def transcribe(self, file_path: str) -> str:
        """
        Transcribe audio/video file using Xinference.

        Args:
            file_path: Path to audio/video file

        Returns:
            Transcribed text

        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            from xinference.client import Client

            self.logger.info(f"Starting Xinference transcription for {file_path}")

            # Get client and model
            client = Client(self.xinference_url)
            model = client.get_model(self.model_uid)

            # Read file content as bytes
            with open(file_path, "rb") as audio_file:
                audio_bytes = audio_file.read()

            # Run transcription in executor (sync method)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, model.transcriptions, audio_bytes
            )

            # Extract text from result
            transcript = result.get("text", "") if isinstance(result, dict) else str(result)

            self.logger.info(f"Completed Xinference transcription for {file_path}")
            return transcript

        except ImportError as e:
            self.logger.error("Xinference client library not installed")
            raise TranscriptionError(
                "Xinference client not installed. Please run 'pip install xinference'."
            ) from e
        except Exception as e:
            self.logger.error(f"Xinference transcription failed: {e}")
            raise TranscriptionError(f"Transcription failed: {e}") from e
