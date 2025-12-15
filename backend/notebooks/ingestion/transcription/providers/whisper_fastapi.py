"""
Whisper-FastAPI transcription provider.
"""

import logging
import os

import aiohttp

from ...exceptions import TranscriptionError
from ..client import TranscriptionClient


class WhisperFastapiProvider(TranscriptionClient):
    """Whisper-FastAPI transcription implementation."""

    def __init__(
        self,
        whisper_api_base_url: str = "http://localhost:5005",
        vad_filter: bool = True,
        language: str = "und",
        logger: logging.Logger | None = None,
    ):
        super().__init__(logger)
        self.whisper_api_base_url = whisper_api_base_url.rstrip("/")
        self.vad_filter = vad_filter
        self.language = language

    async def transcribe(self, file_path: str) -> str:
        """
        Transcribe audio/video file using Whisper-FastAPI.

        Args:
            file_path: Path to audio/video file

        Returns:
            Transcribed text

        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            self.logger.info(f"Starting Whisper-FastAPI transcription for {file_path}")

            # Prepare the endpoint URL
            url = f"{self.whisper_api_base_url}/v1/audio/transcriptions"

            # Prepare form data
            data = aiohttp.FormData()

            # Add the audio file
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as audio_file:
                data.add_field(
                    "file",
                    audio_file,
                    filename=filename,
                    content_type="application/octet-stream",
                )

                # Add parameters
                data.add_field("response_format", "json")
                data.add_field("task", "transcribe")
                data.add_field("language", self.language)
                data.add_field("vad_filter", str(self.vad_filter).lower())

                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            # Extract text from JSON response
                            # Response can be JsonResult (dict) or string
                            if isinstance(result, dict):
                                transcript = result.get("text", "")
                            else:
                                transcript = str(result)

                            self.logger.info(
                                f"Completed Whisper-FastAPI transcription for {file_path}"
                            )
                            return transcript
                        elif response.status == 422:
                            # Validation error
                            error_detail = await response.json()
                            self.logger.error(
                                f"Whisper-FastAPI validation error: {error_detail}"
                            )
                            raise TranscriptionError(
                                f"Validation error: {error_detail.get('detail', 'Unknown validation error')}"
                            )
                        else:
                            # Other HTTP errors
                            error_text = await response.text()
                            self.logger.error(
                                f"Whisper-FastAPI HTTP error {response.status}: {error_text}"
                            )
                            raise TranscriptionError(
                                f"HTTP {response.status}: {error_text}"
                            )

        except aiohttp.ClientError as e:
            self.logger.error(f"Whisper-FastAPI connection error: {e}")
            raise TranscriptionError(
                f"Failed to connect to Whisper-FastAPI at {self.whisper_api_base_url}: {e}"
            ) from e
        except FileNotFoundError as e:
            self.logger.error(f"Audio file not found: {file_path}")
            raise TranscriptionError(f"Audio file not found: {file_path}") from e
        except TranscriptionError:
            # Re-raise TranscriptionError as-is
            raise
        except Exception as e:
            self.logger.error(f"Whisper-FastAPI transcription failed: {e}")
            raise TranscriptionError(f"Transcription failed: {e}") from e
