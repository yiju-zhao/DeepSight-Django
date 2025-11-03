"""
WhisperX transcription provider with alignment and optional diarization.
"""

import asyncio
import logging
import os
import threading
from typing import Optional

from ...exceptions import TranscriptionError
from ..client import TranscriptionClient


class WhisperXProvider(TranscriptionClient):
    """WhisperX transcription implementation with word-level alignment."""

    def __init__(
        self,
        model_name: str = "large-v3",
        device: str = "auto",
        compute_type: Optional[str] = None,
        batch_size: int = 16,
        language: Optional[str] = None,
        use_vad: bool = False,
        hf_cache_dir: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize WhisperX provider.

        Args:
            model_name: Whisper model name (tiny, base, small, medium, large-v2, large-v3)
            device: Device to use ('auto', 'cuda', 'cpu')
            compute_type: Compute type for CTranslate2 (float16, int8, etc.)
            batch_size: Batch size for transcription
            language: Language code (e.g., 'en', 'zh'). If None, auto-detect.
            use_vad: Enable voice activity detection (experimental)
            hf_cache_dir: Optional custom HuggingFace cache directory
            logger: Optional logger instance
        """
        super().__init__(logger)
        self.model_name = model_name
        self.device_config = device
        self.compute_type = compute_type
        self.batch_size = batch_size
        self.language = language
        self.use_vad = use_vad
        self.hf_cache_dir = hf_cache_dir

        # Lazy-loaded components
        self.model = None
        self.align_model = None
        self.align_meta = None
        self.device = None
        self.load_lock = threading.Lock()

        self.logger.info(
            f"WhisperXProvider initialized: model={model_name}, device={device}, "
            f"compute_type={compute_type}, batch_size={batch_size}, language={language}"
        )

    def _auto_select_device(self) -> str:
        """Auto-select device based on availability."""
        if self.device_config != "auto":
            return self.device_config

        try:
            import torch

            if torch.cuda.is_available():
                self.logger.info("CUDA available, using GPU")
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.logger.info("MPS available, using Apple Silicon GPU")
                return "mps"
            else:
                self.logger.info("No GPU available, using CPU")
                return "cpu"
        except ImportError:
            self.logger.warning("PyTorch not available, defaulting to CPU")
            return "cpu"

    def _auto_select_compute_type(self, device: str) -> str:
        """Auto-select compute type based on device."""
        if self.compute_type is not None:
            return self.compute_type

        if device == "cuda":
            return "float16"
        elif device == "cpu":
            return "int8"
        else:  # mps or other
            return "float32"

    def _load_models(self):
        """Lazy-load WhisperX models (thread-safe)."""
        with self.load_lock:
            if self.model is not None:
                return  # Already loaded

            try:
                import whisperx
            except ImportError as e:
                self.logger.error("WhisperX library not installed")
                raise TranscriptionError(
                    "WhisperX not installed. Please run: pip install whisperx\n"
                    "For GPU support, also install PyTorch with CUDA: "
                    "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
                ) from e

            self.logger.info("Loading WhisperX models...")

            # Select device
            self.device = self._auto_select_device()
            compute_type = self._auto_select_compute_type(self.device)

            self.logger.info(
                f"Device: {self.device}, Compute type: {compute_type}, Cache: {self.hf_cache_dir or 'default'}"
            )

            # Load Whisper model
            try:
                self.model = whisperx.load_model(
                    self.model_name,
                    self.device,
                    compute_type=compute_type,
                    download_root=self.hf_cache_dir,
                )
                self.logger.info(f"Loaded Whisper model: {self.model_name}")
            except Exception as e:
                self.logger.error(f"Failed to load Whisper model: {e}")
                raise TranscriptionError(
                    f"Failed to load Whisper model '{self.model_name}': {e}"
                ) from e

    def _load_align_models(self, language_code: str):
        """Load alignment models for a specific language."""
        if self.align_model is not None and hasattr(self, "_align_language"):
            if self._align_language == language_code:
                return  # Already loaded for this language

        try:
            import whisperx

            self.logger.info(f"Loading alignment model for language: {language_code}")
            self.align_model, self.align_meta = whisperx.load_align_model(
                language_code=language_code,
                device=self.device,
            )
            self._align_language = language_code
            self.logger.info(f"Loaded alignment model for: {language_code}")
        except Exception as e:
            self.logger.warning(
                f"Failed to load alignment model for '{language_code}': {e}. "
                "Continuing without alignment."
            )
            self.align_model = None
            self.align_meta = None

    async def transcribe(self, file_path: str) -> str:
        """
        Transcribe audio/video file using WhisperX with alignment.

        Args:
            file_path: Path to audio/video file

        Returns:
            Transcribed text with word-level timestamps (plain text)

        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            # Lazy-load models if not already loaded
            if self.model is None:
                self._load_models()

            import whisperx

            self.logger.info(f"Starting WhisperX transcription for {file_path}")

            # Load audio (supports various formats via ffmpeg)
            loop = asyncio.get_running_loop()
            audio = await loop.run_in_executor(
                None, whisperx.load_audio, file_path
            )

            # Run transcription
            self.logger.info("Running Whisper transcription...")
            transcribe_kwargs = {
                "audio": audio,
                "batch_size": self.batch_size,
            }
            if self.language:
                transcribe_kwargs["language"] = self.language

            if self.use_vad:
                # VAD filter can improve results but may be slower
                transcribe_kwargs["vad_filter"] = True

            result = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(**transcribe_kwargs)
            )

            # Detect language if not specified
            detected_language = result.get("language", self.language or "en")
            self.logger.info(f"Detected/using language: {detected_language}")

            # Load alignment model for detected language
            self._load_align_models(detected_language)

            # Align if alignment model is available
            if self.align_model is not None and self.align_meta is not None:
                self.logger.info("Running word-level alignment...")
                aligned_result = await loop.run_in_executor(
                    None,
                    lambda: whisperx.align(
                        result["segments"],
                        self.align_model,
                        self.align_meta,
                        audio,
                        self.device,
                        return_char_alignments=False,
                    )
                )
                segments = aligned_result["segments"]
            else:
                # Use unaligned segments
                segments = result["segments"]

            # Extract text from segments
            transcript_lines = []
            for segment in segments:
                text = segment.get("text", "").strip()
                if text:
                    transcript_lines.append(text)

            transcript = "\n".join(transcript_lines)

            self.logger.info(
                f"Completed WhisperX transcription for {file_path}: "
                f"{len(transcript)} characters, {len(segments)} segments"
            )

            return transcript

        except ImportError as e:
            self.logger.error("WhisperX dependencies not available")
            raise TranscriptionError(
                "WhisperX not properly installed. Please check dependencies: "
                "pip install whisperx, and ensure ffmpeg is installed."
            ) from e
        except Exception as e:
            self.logger.error(f"WhisperX transcription failed: {e}")
            raise TranscriptionError(f"Transcription failed: {e}") from e

    def close(self):
        """Free GPU/CPU resources by clearing loaded models."""
        self.logger.info("Closing WhisperX provider and freeing resources...")
        self.model = None
        self.align_model = None
        self.align_meta = None

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                self.logger.info("Cleared CUDA cache")
        except Exception as e:
            self.logger.debug(f"Could not clear CUDA cache: {e}")
