"""
Ingestion Orchestrator - Single entry point for all ingestion operations.
"""

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Optional

from ..processors.minio_post_processor import MinIOPostProcessor
from ..utils.helpers import clean_title
from ..utils.storage import FileStorageService
from .exceptions import IngestionError, ParseError, SourceError, StorageError
from .parsers import MediaParser, PdfParser, ParseResult, TextParser
from .transcription import WhisperXProvider, XinferenceProvider
from .url_fetcher import UrlFetcher


@dataclass
class IngestionResult:
    """Result of ingestion operation."""

    file_id: str
    status: str
    parsing_status: str
    features_available: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    content_preview: str = ""


class IngestionOrchestrator:
    """
    Unified orchestrator for file and URL ingestion.
    Coordinates download/parse/store/post-process pipeline.
    """

    def __init__(
        self,
        mineru_base_url: str = "http://localhost:8008",
        transcription_provider: str = "whisperx",
        # WhisperX configuration
        whisperx_model_name: str = "large-v2",
        whisperx_device: str = "auto",
        whisperx_compute_type: Optional[str] = None,
        whisperx_batch_size: int = 16,
        whisperx_language: Optional[str] = None,
        whisperx_use_vad: bool = False,
        whisperx_cache_dir: Optional[str] = None,
        # Xinference configuration (fallback)
        xinference_url: str = "http://localhost:9997",
        xinference_model_uid: str = "Bella-whisper-large-v3-zh",
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)

        # Initialize components
        self.url_fetcher = UrlFetcher(logger=self.logger)

        # Initialize transcription client based on provider
        transcription_client = self._initialize_transcription_client(
            provider=transcription_provider,
            whisperx_model_name=whisperx_model_name,
            whisperx_device=whisperx_device,
            whisperx_compute_type=whisperx_compute_type,
            whisperx_batch_size=whisperx_batch_size,
            whisperx_language=whisperx_language,
            whisperx_use_vad=whisperx_use_vad,
            whisperx_cache_dir=whisperx_cache_dir,
            xinference_url=xinference_url,
            xinference_model_uid=xinference_model_uid,
        )

        self.pdf_parser = PdfParser(
            mineru_base_url=mineru_base_url,
            logger=self.logger,
        )

        self.media_parser = MediaParser(
            transcription_client=transcription_client,
            logger=self.logger,
        )

        self.text_parser = TextParser(logger=self.logger)

        # Initialize storage and post-processor
        self.file_storage = FileStorageService()
        self.post_processor = MinIOPostProcessor(
            file_storage_service=self.file_storage,
            logger=self.logger,
        )

        self.logger.info("IngestionOrchestrator initialized")

    def _initialize_transcription_client(
        self,
        provider: str,
        whisperx_model_name: str,
        whisperx_device: str,
        whisperx_compute_type: Optional[str],
        whisperx_batch_size: int,
        whisperx_language: Optional[str],
        whisperx_use_vad: bool,
        whisperx_cache_dir: Optional[str],
        xinference_url: str,
        xinference_model_uid: str,
    ):
        """
        Initialize transcription client based on provider configuration.

        Args:
            provider: Provider name ('whisperx' or 'xinference')
            ... (other args for configuration)

        Returns:
            TranscriptionClient instance
        """
        provider = provider.lower()

        if provider == "whisperx":
            self.logger.info("Initializing WhisperX transcription provider")
            return WhisperXProvider(
                model_name=whisperx_model_name,
                device=whisperx_device,
                compute_type=whisperx_compute_type,
                batch_size=whisperx_batch_size,
                language=whisperx_language,
                use_vad=whisperx_use_vad,
                hf_cache_dir=whisperx_cache_dir,
                logger=self.logger,
            )

        elif provider == "xinference":
            self.logger.info("Initializing Xinference transcription provider")
            return XinferenceProvider(
                xinference_url=xinference_url,
                model_uid=xinference_model_uid,
                logger=self.logger,
            )

        else:
            raise ValueError(
                f"Unknown transcription provider: {provider}. "
                "Must be 'whisperx' or 'xinference'."
            )

    async def ingest_url(
        self,
        url: str,
        user_pk: int,
        notebook_id: int,
        mode: Literal["webpage", "document", "media"],
        kb_item_id: Optional[str] = None,
    ) -> IngestionResult:
        """
        Ingest content from URL.

        Args:
            url: URL to ingest
            user_pk: User ID
            notebook_id: Notebook ID
            mode: Fetch mode (webpage/document/media)
            kb_item_id: Optional KB item ID to update

        Returns:
            IngestionResult with file_id and status
        """
        temp_files = []
        temp_dirs = []

        try:
            self.logger.info(f"Ingesting URL ({mode}): {url}")

            # Step 1: Fetch URL
            fetch_result = await self.url_fetcher.fetch(url, mode=mode)

            # Step 2: Parse based on fetch type
            if fetch_result.fetch_type == "webpage":
                # Web content, use TextParser with in-memory content
                metadata = {
                    "filename": f"{fetch_result.metadata.get('title', 'webpage')}.md",
                    "file_extension": ".md",
                    "content": fetch_result.content,  # Pass content directly
                    "source_url": url,
                }
                parse_result = await self.text_parser.parse(None, metadata)

            elif fetch_result.fetch_type == "document":
                # Downloaded document
                temp_files.append(fetch_result.local_path)

                # Determine parser based on extension
                extension = fetch_result.metadata.get("extension", "").lower()
                metadata = {
                    "filename": fetch_result.filename,
                    "file_extension": extension,
                    "source_url": url,
                    **fetch_result.metadata,
                }

                if extension == ".pdf":
                    parse_result = await self.pdf_parser.parse(
                        fetch_result.local_path, metadata
                    )
                elif extension in [".ppt", ".pptx"]:
                    parse_result = await self.text_parser.parse(
                        fetch_result.local_path, metadata
                    )
                else:
                    raise ParseError(f"Unsupported document extension: {extension}")

            elif fetch_result.fetch_type == "media":
                # Downloaded media
                temp_dirs.append(os.path.dirname(fetch_result.local_path))

                extension = Path(fetch_result.filename).suffix.lower()
                metadata = {
                    "filename": fetch_result.filename,
                    "file_extension": extension,
                    "source_url": url,
                    **fetch_result.metadata,
                }

                parse_result = await self.media_parser.parse(
                    fetch_result.local_path, metadata
                )

            else:
                raise IngestionError(f"Unknown fetch type: {fetch_result.fetch_type}")

            # Step 3: Store processed file
            file_id = await self._store_result(
                parse_result=parse_result,
                metadata=metadata,
                user_pk=user_pk,
                notebook_id=notebook_id,
                original_file_path=fetch_result.local_path,
                source_identifier=url,
                kb_item_id=kb_item_id,
            )

            # Step 4: Post-process MinerU extractions
            if parse_result.marker_extraction_result:
                await self._post_process_mineru(
                    file_id, parse_result.marker_extraction_result
                )

            # Step 5: Clean up temp files
            self._cleanup_temp_files(temp_files, temp_dirs)

            return IngestionResult(
                file_id=file_id,
                status="completed",
                parsing_status="completed",
                features_available=parse_result.features_available,
                metadata=parse_result.metadata,
                content_preview=parse_result.content[:500]
                if parse_result.content
                else "",
            )

        except (SourceError, ParseError, StorageError) as e:
            self.logger.error(f"Ingestion failed: {e}")
            self._cleanup_temp_files(temp_files, temp_dirs)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during ingestion: {e}")
            self._cleanup_temp_files(temp_files, temp_dirs)
            raise IngestionError(f"Ingestion failed: {e}") from e

    async def ingest_file(
        self,
        file_path: str,
        user_pk: int,
        notebook_id: int,
        metadata: dict[str, Any],
        kb_item_id: Optional[str] = None,
    ) -> IngestionResult:
        """
        Ingest uploaded file.

        Args:
            file_path: Path to uploaded file
            user_pk: User ID
            notebook_id: Notebook ID
            metadata: File metadata (filename, extension, etc.)
            kb_item_id: Optional KB item ID to update

        Returns:
            IngestionResult with file_id and status
        """
        temp_files = []

        try:
            self.logger.info(f"Ingesting file: {file_path}")

            # Determine parser based on extension
            extension = metadata.get("file_extension", "").lower()

            if extension == ".pdf":
                parse_result = await self.pdf_parser.parse(file_path, metadata)
            elif extension in [
                ".mp3",
                ".wav",
                ".m4a",
                ".mp4",
                ".avi",
                ".mov",
                ".mkv",
                ".webm",
                ".flv",
                ".wmv",
                ".3gp",
                ".ogv",
                ".m4v",
            ]:
                parse_result = await self.media_parser.parse(file_path, metadata)
            elif extension in [".md", ".txt", ".doc", ".docx", ".ppt", ".pptx"]:
                parse_result = await self.text_parser.parse(file_path, metadata)
            else:
                raise ParseError(f"Unsupported file extension: {extension}")

            # Store result
            file_id = await self._store_result(
                parse_result=parse_result,
                metadata=metadata,
                user_pk=user_pk,
                notebook_id=notebook_id,
                original_file_path=file_path,
                source_identifier=metadata.get("filename", "unknown"),
                kb_item_id=kb_item_id,
            )

            # Post-process MinerU extractions
            if parse_result.marker_extraction_result:
                await self._post_process_mineru(
                    file_id, parse_result.marker_extraction_result
                )

            return IngestionResult(
                file_id=file_id,
                status="completed",
                parsing_status="completed",
                features_available=parse_result.features_available,
                metadata=parse_result.metadata,
                content_preview=parse_result.content[:500]
                if parse_result.content
                else "",
            )

        except (ParseError, StorageError) as e:
            self.logger.error(f"File ingestion failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during file ingestion: {e}")
            raise IngestionError(f"File ingestion failed: {e}") from e

    async def _store_result(
        self,
        parse_result: ParseResult,
        metadata: dict[str, Any],
        user_pk: int,
        notebook_id: int,
        original_file_path: Optional[str],
        source_identifier: str,
        kb_item_id: Optional[str],
    ) -> str:
        """Store parsing result using FileStorageService."""
        try:
            from asgiref.sync import sync_to_async

            # Prepare full metadata
            full_metadata = {
                "original_filename": metadata.get("filename", "Untitled"),
                "file_extension": metadata.get("file_extension", ""),
                "content_type": metadata.get("content_type", ""),
                "file_size": metadata.get(
                    "file_size", len(parse_result.content.encode("utf-8"))
                ),
                "source_url": metadata.get("source_url"),
                "upload_timestamp": datetime.now(UTC).isoformat(),
                "parsing_status": "completed",
                **parse_result.metadata,
            }

            # Prepare processing result
            processing_result = {
                "features_available": parse_result.features_available,
                "processing_time": "immediate",
            }

            # For MinerU PDFs, skip content file
            if parse_result.marker_extraction_result:
                processing_result["skip_content_file"] = True
                processing_result["content_filename"] = (
                    f"{parse_result.marker_extraction_result['clean_title']}.md"
                )

            # Call storage in executor
            store_sync = sync_to_async(
                self.file_storage.store_processed_file,
                thread_sensitive=False,
            )

            file_id = await store_sync(
                content=parse_result.content,
                metadata=full_metadata,
                processing_result=processing_result,
                user_id=user_pk,
                notebook_id=notebook_id,
                original_file_path=original_file_path,
                source_identifier=source_identifier,
                kb_item_id=kb_item_id,
            )

            self.logger.info(f"Stored file with ID: {file_id}")
            return file_id

        except Exception as e:
            self.logger.error(f"Storage failed: {e}")
            raise StorageError(f"Failed to store file: {e}") from e

    async def _post_process_mineru(
        self,
        file_id: str,
        marker_extraction_result: dict[str, Any],
    ):
        """Post-process MinerU extraction results."""
        try:
            from asgiref.sync import sync_to_async

            post_process_sync = sync_to_async(
                self.post_processor.post_process_mineru_extraction,
                thread_sensitive=False,
            )

            await post_process_sync(file_id, marker_extraction_result)

            self.logger.info(f"Completed MinerU post-processing for file {file_id}")

        except Exception as e:
            self.logger.error(f"MinerU post-processing failed: {e}")
            # Don't raise - post-processing failure shouldn't fail entire ingestion

    def _cleanup_temp_files(
        self,
        temp_files: list[str],
        temp_dirs: list[str],
    ):
        """Clean up temporary files and directories."""
        for temp_file in temp_files:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {temp_file}: {e}")

        for temp_dir in temp_dirs:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"Cleaned up temp dir: {temp_dir}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {temp_dir}: {e}")
