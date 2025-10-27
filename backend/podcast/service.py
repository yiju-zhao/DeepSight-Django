"""
Podcast Service using Panel Discussion Agent Framework

This service simplifies podcast generation by leveraging the
panel discussion framework to create conversation and then convert to audio.
"""

import logging
from pathlib import Path
from typing import Any

from django.utils import timezone

from .storage import PodcastStorageService
from .utils import (
    extract_selected_content,
    generate_conversation_audio_optimized,
    parse_bracket_turns,
    parse_conversation,
)

logger = logging.getLogger(__name__)


class PodcastService:
    """
    Podcast service that uses the panel discussion framework
    to generate conversations and convert them to audio.
    """

    def __init__(self):
        """Initialize the podcast service with storage"""
        self.storage_service = PodcastStorageService()

    async def create_podcast_with_panel_crew(
        self,
        selected_item_ids: list[int],
        user_id: int,
        podcast_id: str,
        notebook_id: int | None = None,
        custom_instruction: str = None,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Create a podcast from selected knowledge base items using panel_crew.

        Args:
            selected_item_ids: List of KnowledgeBaseItem IDs selected by frontend
            user_id: User ID for the podcast
            podcast_id: Podcast ID for the podcast
            notebook_id: Notebook ID (optional)
            custom_instruction: Optional custom discussion instruction
            language: Language for the podcast (en or zh), default 'en'

        Returns:
            Dictionary with conversation result and metadata
        """
        try:
            # Extract content from selected items
            selected_content = await extract_selected_content(selected_item_ids)

            # Create topic with custom instruction
            topic = custom_instruction if custom_instruction else ""

            # Run panel crew discussion
            from agents.panel_crew import PanelCrewCollaboration

            # Create crew with material content
            panel_crew = PanelCrewCollaboration(material_content=selected_content)

            # Prepare language instruction for the crew
            language_instruction = "中文" if language == "zh" else "English"

            logger.info(
                f"Starting panel crew discussion for topic: {topic} in {language_instruction}"
            )
            # Knowledge-base only: only pass topic and language; materials are in knowledge_sources
            result = panel_crew.crew().kickoff(
                inputs={
                    "topic": topic,
                    "language": language_instruction,
                }
            )

            # Extract title only; keep conversation text unchanged
            title, conversation_text = parse_conversation(str(result))
            # Convert bracket-formatted conversation into turns for TTS
            conversation_turns = parse_bracket_turns(conversation_text)

            if not conversation_turns:
                raise Exception("No conversation turns extracted from panel discussion")

            # Use generated title or fallback to default
            podcast_title = title if title else "Panel Conversation"
            logger.info(f"Using podcast title: {podcast_title}")

            # Convert to audio and store in MinIO
            audio_object_key = self._process_conversation_to_audio(
                conversation_turns, user_id, podcast_id, notebook_id, language
            )

            # If audio generation/storage failed, treat as failure
            if not audio_object_key:
                raise Exception("Audio generation failed: no audio object key produced")

            return {
                "status": "completed",
                "conversation_turns": conversation_turns,
                "crew_result": str(result),  # Convert crew result to string
                "audio_object_key": audio_object_key,
                "title": podcast_title,
                "metadata": {
                    "total_turns": len(conversation_turns),
                    "participants": list(
                        {turn["speaker"] for turn in conversation_turns}
                    ),
                    "generated_at": timezone.now().isoformat(),
                    "selected_items_count": len(selected_item_ids),
                    "topic": topic,
                },
            }

        except Exception as e:
            logger.error(
                f"Panel crew podcast creation failed for selected items {selected_item_ids}: {e}"
            )
            return {
                "status": "failed",
                "error": str(e),
                "conversation_turns": None,
                "crew_result": None,
                "audio_object_key": None,
            }

    def _process_conversation_to_audio(
        self,
        conversation_turns: list[dict[str, str]],
        user_id: int,
        podcast_id: str,
        notebook_id: int | None = None,
        language: str = "en",
    ) -> str | None:
        """
        Main orchestration method for converting conversation to audio and storing in MinIO.

        Args:
            conversation_turns: Already parsed conversation turns
            user_id: User ID for the podcast
            podcast_id: Podcast ID for the podcast
            notebook_id: Notebook ID (optional)
            language: Language for the podcast (en or zh), default 'en'

        Returns:
            MinIO object key for the stored audio file, or None if failed
        """
        try:
            import tempfile

            # Create temporary directory for audio processing
            temp_dir = Path(tempfile.mkdtemp())

            try:
                # Generate audio file using optimized approach from utils
                audio_file_path = generate_conversation_audio_optimized(
                    conversation_turns, temp_dir, language
                )

                # Store in MinIO using storage service
                if audio_file_path:
                    return self._store_audio_with_metadata(
                        audio_file_path,
                        conversation_turns,
                        user_id,
                        podcast_id,
                        notebook_id,
                    )

                return None

            finally:
                # Clean up temporary directory
                import shutil

                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to clean up temp directory {temp_dir}: {cleanup_error}"
                    )

        except Exception as e:
            logger.error(f"Conversation to audio processing failed: {e}")
            return None

    def _store_audio_with_metadata(
        self,
        audio_file_path: Path,
        conversation_turns: list[dict[str, str]],
        user_id: int,
        podcast_id: str,
        notebook_id: int | None = None,
    ) -> str | None:
        """
        Store audio file using storage service with conversation metadata.

        Args:
            audio_file_path: Path to audio file to store
            conversation_turns: List of conversation turns for metadata
            user_id: User ID for the podcast
            podcast_id: Podcast ID for the podcast
            notebook_id: Notebook ID (optional)

        Returns:
            MinIO object key for stored file, or None if failed
        """
        try:
            # Prepare metadata from conversation
            metadata = {
                "total_turns": len(conversation_turns),
                "participants": list({turn["speaker"] for turn in conversation_turns}),
                "generated_at": timezone.now().isoformat(),
            }

            # Store using storage service
            storage_result = self.storage_service.store_podcast_audio(
                audio_file_path, user_id, podcast_id, notebook_id, metadata
            )

            if storage_result["storage_success"]:
                return storage_result["audio_object_key"]
            else:
                logger.error(f"Storage service failed: {storage_result['error']}")
                return None

        except Exception as e:
            logger.error(f"Audio storage with metadata failed: {e}")
            return None
