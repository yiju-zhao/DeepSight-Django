"""
Transcription providers.
"""

from .xinference import XinferenceProvider
from .whisper_fastapi import WhisperFastapiProvider

__all__ = ["XinferenceProvider", "WhisperFastapiProvider"]
