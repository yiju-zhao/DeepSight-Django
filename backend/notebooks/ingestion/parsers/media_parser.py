"""
Media parser for audio and video files with transcription support.
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

from ...utils.helpers import clean_title
from ..exceptions import ParseError, TranscriptionError
from ..transcription import TranscriptionClient
from .base_parser import BaseParser, ParseResult


class MediaParser(BaseParser):
    """Parser for audio and video files with transcription."""

    def __init__(
        self,
        transcription_client: TranscriptionClient,
        logger: Optional[logging.Logger] = None,
    ):
        self.transcription_client = transcription_client
        self.logger = logger or logging.getLogger(__name__)

    async def parse(self, file_path: str, metadata: dict[str, Any]) -> ParseResult:
        """
        Parse audio/video file and transcribe.

        Args:
            file_path: Path to audio/video file
            metadata: File metadata (filename, extension, etc.)

        Returns:
            ParseResult with transcribed content and metadata
        """
        file_extension = metadata.get("file_extension", "").lower()

        # Determine if audio or video
        audio_extensions = [".mp3", ".wav", ".m4a"]
        video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".3gp", ".ogv", ".m4v"]

        if file_extension in audio_extensions:
            return await self._parse_audio(file_path, metadata)
        elif file_extension in video_extensions:
            return await self._parse_video(file_path, metadata)
        else:
            raise ParseError(f"Unsupported media file extension: {file_extension}")

    async def _parse_audio(
        self, file_path: str, metadata: dict[str, Any]
    ) -> ParseResult:
        """Parse audio file with transcription."""
        self.logger.info(f"Parsing audio file: {file_path}")

        try:
            # Transcribe audio
            transcript_content = await self.transcription_client.transcribe(file_path)

            # Generate transcript filename
            base_title = Path(metadata["filename"]).stem
            cleaned_title = clean_title(base_title)
            transcript_filename = f"{cleaned_title}.md"

            # Get audio metadata
            audio_metadata = self._get_audio_metadata(file_path)
            audio_metadata.update({
                "transcript_filename": transcript_filename,
                "has_transcript": True,
            })

            return ParseResult(
                content=transcript_content,
                metadata=audio_metadata,
                features_available=[
                    "speaker_diarization",
                    "sentiment_analysis",
                    "advanced_audio_analysis",
                ],
            )

        except TranscriptionError as e:
            # Transcription failed, return basic info
            self.logger.warning(f"Transcription failed: {e}")
            audio_metadata = self._get_audio_metadata(file_path)
            audio_metadata["transcription_failed"] = str(e)

            return ParseResult(
                content=f"# Audio: {metadata['filename']}\n\nTranscription service unavailable: {e}",
                metadata=audio_metadata,
                features_available=["audio_metadata"],
            )

    async def _parse_video(
        self, file_path: str, metadata: dict[str, Any]
    ) -> ParseResult:
        """Parse video file with optional transcription."""
        self.logger.info(f"Parsing video file: {file_path}")

        # Extract audio from video for transcription
        audio_path = tempfile.mktemp(suffix=".wav")

        cmd = [
            "ffmpeg",
            "-i", file_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            audio_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Initialize content
        content_parts = []

        # Generate transcript filename
        base_title = Path(metadata["filename"]).stem
        cleaned_title = clean_title(base_title)
        transcript_filename = f"{cleaned_title}.md"
        has_transcript = False

        # Try transcription if audio extraction succeeded
        if result.returncode == 0 and os.path.exists(audio_path):
            try:
                transcript_content = await self.transcription_client.transcribe(audio_path)
                content_parts.append(f"# Transcription\n\n{transcript_content}")
                has_transcript = True
            except TranscriptionError as e:
                self.logger.warning(f"Video transcription failed: {e}")
                content_parts.append(
                    f"# Video: {metadata['filename']}\n\n"
                    f"Transcription failed: {e}"
                )
            finally:
                # Clean up extracted audio
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
        else:
            # No audio or extraction failed
            if result.returncode != 0:
                content_parts.append(
                    f"# Video: {metadata['filename']}\n\n"
                    f"No audio track found or audio extraction failed."
                )
            else:
                content_parts.append(
                    f"# Video: {metadata['filename']}\n\n"
                    f"Audio transcription service not available."
                )

        # Get video metadata
        video_metadata = self._get_video_metadata(file_path)
        video_metadata.update({
            "transcript_filename": transcript_filename,
            "has_transcript": has_transcript,
            "has_audio": result.returncode == 0,
        })

        # Combine content
        final_content = "\n\n".join(content_parts)

        return ParseResult(
            content=final_content,
            metadata=video_metadata,
            features_available=[
                "frame_extraction",
                "scene_analysis",
                "speaker_diarization",
                "video_analysis",
            ],
        )

    def _get_audio_metadata(self, file_path: str) -> dict[str, Any]:
        """Extract audio metadata using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                file_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            data = json.loads(result.stdout)
            format_info = data.get("format", {})

            return {
                "duration": float(format_info.get("duration", 0)),
                "bitrate": int(format_info.get("bit_rate", 0)),
                "size": int(format_info.get("size", 0)),
                "format_name": format_info.get("format_name", "unknown"),
            }
        except Exception as e:
            self.logger.warning(f"Could not extract audio metadata: {e}")
            return {"error": "Could not extract audio metadata"}

    def _get_video_metadata(self, file_path: str) -> dict[str, Any]:
        """Extract video metadata using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                file_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            data = json.loads(result.stdout)

            # Get video stream info
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {},
            )
            format_info = data.get("format", {})

            return {
                "duration": float(format_info.get("duration", 0)),
                "resolution": f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
                "fps": video_stream.get("r_frame_rate", "0/0"),
                "codec": video_stream.get("codec_name", "unknown"),
                "format_name": format_info.get("format_name", "unknown"),
                "size": int(format_info.get("size", 0)),
            }
        except Exception as e:
            self.logger.warning(f"Could not extract video metadata: {e}")
            return {"error": "Could not extract video metadata"}
