"""
Transcription Service - Handle audio/video transcription using faster-whisper.
"""
import time
import logging
import asyncio
from pathlib import Path
from typing import Tuple


class TranscriptionService:
    """Handle audio/video transcription using faster-whisper."""
    
    def __init__(self, whisper_model, clean_title_func=None, logger=None):
        self.whisper_model = whisper_model
        self.clean_title = clean_title_func
        self.logger = logger or logging.getLogger(__name__)
    
    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log operations with consistent formatting."""
        message = f"[transcription_service] {operation}"
        if details:
            message += f": {details}"
        getattr(self.logger, level)(message)

    def _hh_mm_ss(self, s: float) -> str:
        """Convert seconds to HH:MM:SS format."""
        import datetime as dt
        return str(dt.timedelta(seconds=int(s)))

    async def transcribe_audio_video(self, file_path: str, filename: str) -> Tuple[str, str]:
        """Transcribe audio/video file using faster-whisper. Returns (transcript_content, suggested_filename)."""
        try:
            self.log_operation("transcription_start", f"Starting transcription of {file_path}")
            start_time = time.time()

            if not self.whisper_model:
                raise Exception("Speech-to-text not available. Please install faster-whisper and torch.")
            
            # Run transcription in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            
            def _transcribe_sync():
                return self.whisper_model.transcribe(file_path, vad_filter=True, batch_size=16)
            
            # Execute the CPU-intensive transcription in a thread pool
            segments, _ = await loop.run_in_executor(None, _transcribe_sync)
            
            # Clean the title for filename
            base_title = Path(filename).stem  # Remove file extension
            if self.clean_title:
                cleaned_title = self.clean_title(base_title)
            else:
                cleaned_title = base_title
            suggested_filename = f"{cleaned_title}.md"
            
            # Build the transcript
            transcript_lines = []
   
            for segment in segments:
                timestamp = self._hh_mm_ss(segment.start)
                transcript_lines.append(f"**{timestamp}** {segment.text}\\n")
            
            transcript_content = "\\n".join(transcript_lines)
            
            end_time = time.time()
            duration = end_time - start_time
            self.log_operation("transcription_completed", f"Transcription completed in {duration:.2f} seconds ({duration/60:.2f} minutes)")
            
            return transcript_content, suggested_filename
            
        except Exception as e:
            self.log_operation("transcription_error", f"Transcription failed: {e}", "error")
            raise Exception(f"Transcription failed: {str(e)}")