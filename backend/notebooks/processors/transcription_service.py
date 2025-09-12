"""
Transcription Service - Handle audio/video transcription using Xinference.
"""
import time
import logging
import asyncio
import os
from pathlib import Path
from typing import Tuple, Optional
from xinference.client import Client


class TranscriptionService:
    """Handle audio/video transcription using Xinference."""
    
    def __init__(self, xinference_url: str = None, model_uid: str = None, clean_title_func=None, logger=None):
        self.xinference_url = xinference_url or os.getenv('XINFERENCE_URL', 'http://localhost:9997')
        self.model_uid = model_uid or os.getenv('XINFERENCE_WHISPER_MODEL_UID', 'whisper-large-v3-turbo')
        self.clean_title = clean_title_func
        self.logger = logger or logging.getLogger(__name__)
        self._client = None
        self._model = None
    
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
    
    def _get_client(self):
        """Get or create Xinference client."""
        if not self._client:
            try:
                self._client = Client(self.xinference_url)
                self.log_operation("xinference_client_connected", f"Connected to Xinference at {self.xinference_url}")
            except Exception as e:
                self.log_operation("xinference_client_error", f"Failed to connect to Xinference: {e}", "error")
                raise Exception(f"Failed to connect to Xinference at {self.xinference_url}: {str(e)}")
        return self._client
    
    def _get_model(self):
        """Get or create Xinference model."""
        if not self._model:
            try:
                client = self._get_client()
                self._model = client.get_model(self.model_uid)
                self.log_operation("xinference_model_loaded", f"Loaded model {self.model_uid}")
            except Exception as e:
                self.log_operation("xinference_model_error", f"Failed to load model {self.model_uid}: {e}", "error")
                raise Exception(f"Failed to load model {self.model_uid}: {str(e)}")
        return self._model

    async def transcribe_audio_video(self, file_path: str, filename: str) -> Tuple[str, str]:
        """Transcribe audio/video file using Xinference. Returns (transcript_content, suggested_filename)."""
        try:
            self.log_operation("transcription_start", f"Starting transcription of {file_path}")
            start_time = time.time()

            # Get the model
            model = self._get_model()
            
            # Read audio file
            with open(file_path, "rb") as audio_file:
                audio_data = audio_file.read()
            
            # Run transcription in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            
            def _transcribe_sync():
                return model.transcriptions(audio_data)
            
            # Execute the transcription in a thread pool
            result = await loop.run_in_executor(None, _transcribe_sync)
            
            # Clean the title for filename
            base_title = Path(filename).stem  # Remove file extension
            if self.clean_title:
                cleaned_title = self.clean_title(base_title)
            else:
                cleaned_title = base_title
            suggested_filename = f"{cleaned_title}.md"
            
            # Process the result - check if it has segments or just text
            transcript_lines = []
            
            if hasattr(result, 'segments') and result.segments:
                # If the result has segments with timestamps
                for segment in result.segments:
                    timestamp = self._hh_mm_ss(segment.get('start', 0))
                    text = segment.get('text', '').strip()
                    if text:
                        transcript_lines.append(f"**{timestamp}** {text}\\n")
            elif hasattr(result, 'text') and result.text:
                # If the result only has text without timestamps
                transcript_lines.append(result.text.strip())
            elif isinstance(result, dict):
                # Handle different response formats
                if 'segments' in result:
                    for segment in result['segments']:
                        timestamp = self._hh_mm_ss(segment.get('start', 0))
                        text = segment.get('text', '').strip()
                        if text:
                            transcript_lines.append(f"**{timestamp}** {text}\\n")
                elif 'text' in result:
                    transcript_lines.append(result['text'].strip())
                else:
                    transcript_lines.append(str(result))
            else:
                # Fallback: convert result to string
                transcript_lines.append(str(result).strip())
            
            transcript_content = "\\n".join(transcript_lines) if transcript_lines else "No transcription available"
            
            end_time = time.time()
            duration = end_time - start_time
            self.log_operation("transcription_completed", f"Transcription completed in {duration:.2f} seconds ({duration/60:.2f} minutes)")
            
            return transcript_content, suggested_filename
            
        except Exception as e:
            self.log_operation("transcription_error", f"Transcription failed: {e}", "error")
            raise Exception(f"Transcription failed: {str(e)}")