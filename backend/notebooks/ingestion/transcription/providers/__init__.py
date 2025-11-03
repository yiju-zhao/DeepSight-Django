"""
Transcription providers.
"""

from .whisperx import WhisperXProvider
from .xinference import XinferenceProvider

__all__ = ["WhisperXProvider", "XinferenceProvider"]
