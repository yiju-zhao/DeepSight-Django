"""
URL Fetcher - Unified URL fetching with webpage/document/media support.

Optimized with:
- SSRF protection and security validation
- Simple requests-based HTTP client with timeouts
- Type-safe metadata with TypedDict
- Lazy loading of optional dependencies (magic, crawl4ai, bilix, yt-dlp)
- Structured logging
- Proper temporary directory management
"""

import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict
from urllib.parse import urlparse

from ..utils.helpers import clean_title
from .exceptions import SourceError
from .url_security import validate_url_security


# ============================================================================
# Type Definitions
# ============================================================================


class DocumentMetadata(TypedDict, total=False):
    """Metadata for document fetches."""

    extension: str
    mime_type: str
    size: int
    detected_type: str
    filename: str
    source_url: str


class MediaMetadata(TypedDict, total=False):
    """Metadata for media fetches."""

    has_media: bool
    has_video: bool
    has_audio: bool
    title: str
    duration: int | None
    uploader: str | None
    description: str
    view_count: int | None
    upload_date: str | None
    platform: str
    source_url: str


class WebpageMetadata(TypedDict, total=False):
    """Metadata for webpage fetches."""

    title: str
    description: str
    url: str
    extraction_method: str
    links: list[str]
    images: list[dict]


FetchMode = Literal["webpage", "document", "media"]


@dataclass
class UrlFetchResult:
    """Unified URL fetch result with type-safe metadata."""

    fetch_type: Literal["webpage", "document", "media"]
    content: Optional[str] = None  # For webpage content
    local_path: Optional[str] = None  # For downloaded files
    filename: Optional[str] = None
    metadata: DocumentMetadata | MediaMetadata | WebpageMetadata | dict[str, Any] = (
        field(default_factory=dict)
    )


class UrlFetcher:
    """
    Unified URL fetcher combining webpage, document, and media fetching.

    Features:
    - SSRF protection and URL security validation
    - Simple requests-based downloads with timeouts (30s connect, 5min read)
    - Type-safe metadata (DocumentMetadata, MediaMetadata, WebpageMetadata)
    - Lazy loading of optional dependencies (magic, crawl4ai, bilix, yt-dlp)
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        allow_private_networks: bool = False,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.allow_private_networks = allow_private_networks

        # Lazy-loaded dependencies
        self._crawl4ai_loaded = False
        self._crawl4ai = None
        self._magic_available = None

    async def fetch(
        self, url: str, mode: Literal["webpage", "document", "media"]
    ) -> UrlFetchResult:
        """
        Fetch URL content based on mode.

        Args:
            url: URL to fetch
            mode: Fetch mode (webpage/document/media)

        Returns:
            UrlFetchResult with appropriate content

        Raises:
            SourceError: If fetching fails
        """
        if not self._validate_url(url):
            raise SourceError(f"Invalid URL: {url}")

        if mode == "webpage":
            return await self._fetch_webpage(url)
        elif mode == "document":
            return await self._fetch_document(url)
        elif mode == "media":
            return await self._fetch_media(url)
        else:
            raise ValueError(f"Invalid mode: {mode}")

    def _validate_url(self, url: str) -> bool:
        """
        Validate URL format and security.

        Returns:
            True if URL is valid and safe

        Raises:
            SourceError: If URL is unsafe
        """
        try:
            # Basic format check
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False

            # Security validation with SSRF protection
            is_valid, error_msg = validate_url_security(
                url, self.allow_private_networks
            )
            if not is_valid:
                self.logger.error(f"URL security validation failed: {error_msg}")
                raise SourceError(f"Unsafe URL blocked: {error_msg}")

            return True
        except SourceError:
            raise
        except Exception as e:
            self.logger.error(f"URL validation error: {e}")
            return False

    async def _fetch_webpage(self, url: str) -> UrlFetchResult:
        """Fetch webpage content using crawl4ai."""
        self.logger.info(f"Fetching webpage: {url}")

        await self._load_crawl4ai()

        if not self._crawl4ai_loaded:
            raise SourceError(
                "crawl4ai not available - please ensure crawl4ai is properly installed"
            )

        try:
            config = CrawlerRunConfig(  
                excluded_tags=["nav", "header", "footer"],  
                markdown_generator=DefaultMarkdownGenerator(  
                    content_filter=PruningContentFilter(threshold=0.5)  
                )
            )

            async with self._crawl4ai(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=config
                )

                if not result.success:
                    error_msg = f"Crawl4ai failed with status: {getattr(result, 'status_code', 'unknown')}"
                    if hasattr(result, "error_message") and result.error_message:
                        error_msg += f" - Error: {result.error_message}"
                    raise SourceError(error_msg)

                # Extract content and metadata
                title = result.metadata.get("title", "") if result.metadata else ""
                description = (
                    result.metadata.get("description", "") if result.metadata else ""
                )
                
                # Use fit_markdown if available (filtered content), otherwise raw markdown
                content = ""
                if result.markdown:
                    if hasattr(result.markdown, 'fit_markdown') and result.markdown.fit_markdown:
                        content = result.markdown.fit_markdown
                    elif hasattr(result.markdown, 'raw_markdown'):
                        content = result.markdown.raw_markdown
                    else:
                        content = str(result.markdown)
                
                if not content and result.cleaned_html:
                    content = result.cleaned_html



                metadata = {
                    "title": title,
                    "description": description,
                    "url": url,
                    "extraction_method": "crawl4ai",
                    "links": result.links.get("internal", []) if result.links else [],
                    "images": result.media.get("images", []) if result.media else [],
                }

                return UrlFetchResult(
                    fetch_type="webpage",
                    content=content,
                    metadata=metadata,
                )

        except Exception as e:
            self.logger.error(f"Webpage fetch error: {e}")
            raise SourceError(f"Failed to fetch webpage: {e}") from e

    async def _fetch_document(self, url: str) -> UrlFetchResult:
        """Fetch document file from URL."""
        self.logger.info(f"Fetching document: {url}")

        try:
            # Download to temp file
            temp_file_path = await self._download_to_temp(url)

            # Validate format
            file_info = await self._validate_document_format(temp_file_path)

            if not file_info["is_valid"]:
                # Clean up invalid file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                raise SourceError(
                    f"Invalid document format. Expected PDF or PPTX, got: {file_info['detected_type']}"
                )

            return UrlFetchResult(
                fetch_type="document",
                local_path=temp_file_path,
                filename=file_info["filename"],
                metadata={
                    "extension": file_info["extension"],
                    "mime_type": file_info["mime_type"],
                    "size": file_info["size"],
                    "detected_type": file_info["detected_type"],
                },
            )

        except Exception as e:
            self.logger.error(f"Document fetch error: {e}")
            raise SourceError(f"Failed to fetch document: {e}") from e

    async def _fetch_media(self, url: str) -> UrlFetchResult:
        """Fetch media (audio/video) from URL."""
        self.logger.info(f"Fetching media: {url}")

        # Check if URL is from Bilibili
        parsed_url = urlparse(url)
        is_bilibili = "bilibili.com" in parsed_url.netloc

        if is_bilibili:
            return await self._fetch_bilibili_media(url)

        # Check media availability for other platforms
        media_info = await self._check_media_availability(url)

        if not media_info.get("has_media"):
            error_message = media_info.get(
                "error", "No downloadable media found at the URL."
            )
            raise SourceError(f"Media not available: {error_message}")

        # Download media
        try:
            base_title = media_info.get("title", "media_download")
            base_filename = clean_title(base_title)

            # Limit filename length
            max_base_length = 100
            if len(base_filename) > max_base_length:
                base_filename = base_filename[:max_base_length].rstrip("_")

            # Create temp directory (Note: cleanup is handled by orchestrator via temp_dirs list)
            temp_dir = tempfile.mkdtemp(prefix="deepsight_media_")

            # Download based on media type
            if media_info.get("has_video"):
                downloaded_path = await self._download_video(
                    url, temp_dir, base_filename
                )
            elif media_info.get("has_audio"):
                downloaded_path = await self._download_audio(
                    url, temp_dir, base_filename
                )
            else:
                raise SourceError("Media has neither video nor audio streams")

            if not downloaded_path:
                raise SourceError("Failed to download media file")

            # Get actual filename
            actual_filename = os.path.basename(downloaded_path)

            return UrlFetchResult(
                fetch_type="media",
                local_path=downloaded_path,
                filename=actual_filename,
                metadata=media_info,
            )

        except Exception as e:
            self.logger.error(f"Media fetch error: {e}")
            raise SourceError(f"Failed to fetch media: {e}") from e

    def _download_to_temp_sync(self, url: str) -> tuple[str, str]:
        """
        Download file from URL to temporary location using simple requests.

        Returns:
            (file_path, temp_dir_path) tuple - caller must manage temp_dir cleanup
        """
        import requests

        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="deepsight_download_")

        try:
            self.logger.info(f"Downloading document from: {url}")

            # Simple download with timeout
            timeout = (30, 300)  # (connect, read) in seconds
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(url, timeout=timeout, headers=headers)

            if response.status_code != 200:
                raise SourceError(f"Failed to download: HTTP {response.status_code}")

            # Extract filename from URL or Content-Disposition
            filename = self._extract_filename_from_response(url, response.headers)
            file_path = os.path.join(temp_dir, filename)

            # Save to file
            with open(file_path, "wb") as f:
                f.write(response.content)

            # Fix extension based on content type
            content_type = response.headers.get("content-type", "").lower()
            corrected_path = self._fix_file_extension_sync(file_path, content_type)

            file_size = os.path.getsize(corrected_path)
            self.logger.info(
                f"Downloaded: url={url}, size={file_size}, path={corrected_path}"
            )

            return corrected_path, temp_dir

        except requests.exceptions.Timeout as e:
            # Clean up on error
            if os.path.exists(temp_dir):
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)
            self.logger.error(f"Download timeout: url={url}, error={e}")
            raise SourceError(f"Download timeout: {url}") from e
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_dir):
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)
            self.logger.error(f"Download failed: url={url}, error={e}")
            raise SourceError(f"Failed to download file: {e}") from e

    def _extract_filename_from_response(self, url: str, headers: dict) -> str:
        """Extract filename from URL or Content-Disposition header."""
        filename = None

        # Try Content-Disposition first
        content_disposition = headers.get("content-disposition", "")
        if content_disposition:
            import re

            matches = re.findall(
                r'filename[^;=\n]*=(["\']?)([^"\';]+)\1', content_disposition
            )
            if matches:
                filename = matches[0][1]

        # Fallback to URL path
        if not filename:
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path) or "document"

        # Sanitize filename
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
        filename = filename[:100] if len(filename) > 100 else filename

        return filename or "download"

    async def _download_to_temp(self, url: str) -> str:
        """
        Async wrapper for synchronous download.

        Returns:
            File path (temp directory is managed internally)
        """
        import asyncio

        file_path, _ = await asyncio.to_thread(self._download_to_temp_sync, url)
        # Note: temp_dir cleanup is handled by orchestrator
        return file_path

    def _fix_file_extension_sync(self, file_path: str, content_type: str) -> str:
        """
        Fix file extension based on content type or magic detection (synchronous).

        Uses lazy-loaded python-magic library if available.
        """
        import shutil

        try:
            # Lazy load magic library
            if self._magic_available is None:
                try:
                    import magic as magic_lib

                    self._magic_available = True
                    self._magic = magic_lib
                except ImportError:
                    self._magic_available = False
                    self.logger.warning(
                        "python-magic not available, using Content-Type only"
                    )

            # Detect actual file type using magic if available
            mime_type = None
            if self._magic_available:
                try:
                    mime_type = self._magic.from_file(file_path, mime=True)
                except Exception as e:
                    self.logger.warning(f"Magic detection failed: {e}")

            # Fallback to content-type if magic failed
            if not mime_type:
                mime_type = content_type.split(";")[0].strip() if content_type else ""

            # Determine correct extension
            correct_extension = None
            if mime_type == "application/pdf" or "application/pdf" in content_type:
                correct_extension = ".pdf"
            elif (
                mime_type
                in [
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                ]
                or "powerpoint" in content_type.lower()
            ):
                correct_extension = ".pptx"
            elif mime_type == "application/vnd.ms-powerpoint":
                correct_extension = ".ppt"

            # Fix extension if needed
            if correct_extension:
                current_path = Path(file_path)
                current_extension = current_path.suffix.lower()

                if not current_extension or current_extension != correct_extension:
                    original_name = current_path.name
                    known_extensions = {
                        ".pdf",
                        ".ppt",
                        ".pptx",
                        ".doc",
                        ".docx",
                        ".txt",
                        ".md",
                        ".html",
                        ".htm",
                        ".zip",
                        ".tar",
                        ".gz",
                    }

                    if current_extension and current_extension in known_extensions:
                        original_name = original_name[: -len(current_extension)]

                    clean_base_name = clean_title(original_name)
                    new_filename = clean_base_name + correct_extension
                    new_path = current_path.parent / new_filename

                    shutil.move(str(current_path), str(new_path))
                    self.logger.info(
                        f"Fixed extension: {current_extension} -> {correct_extension}"
                    )
                    return str(new_path)

            return file_path

        except Exception as e:
            self.logger.warning(f"Extension fix error: {e}")
            return file_path

    async def _fix_file_extension(self, file_path: str, content_type: str) -> str:
        """Async wrapper for synchronous extension fix."""
        import asyncio

        return await asyncio.to_thread(
            self._fix_file_extension_sync, file_path, content_type
        )

    def _validate_document_format_sync(self, file_path: str) -> dict[str, Any]:
        """Validate document file format (synchronous)."""
        try:
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)

            # Lazy load magic library if needed
            if self._magic_available is None:
                try:
                    import magic as magic_lib

                    self._magic_available = True
                    self._magic = magic_lib
                except ImportError:
                    self._magic_available = False
                    self.logger.warning(
                        "python-magic not available for file validation"
                    )

            # Detect file type using magic if available
            mime_type = ""
            file_type = ""
            if self._magic_available:
                try:
                    mime_type = self._magic.from_file(file_path, mime=True)
                    file_type = self._magic.from_file(file_path)
                except Exception as e:
                    self.logger.warning(f"Magic detection failed: {e}")

            self.logger.info(
                f"Validating: {filename}, MIME: {mime_type}, Type: {file_type}"
            )

            # Check if valid (gracefully handle missing magic)
            is_pdf = (
                mime_type == "application/pdf"
                or "PDF" in file_type
                or filename.lower().endswith(".pdf")
            )
            is_pptx = (
                mime_type
                == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                or "PowerPoint" in file_type
                or "Microsoft Office" in file_type
                or filename.lower().endswith((".ppt", ".pptx"))
            )

            is_valid = is_pdf or is_pptx

            if is_pdf:
                extension = ".pdf"
                detected_type = "PDF"
            elif is_pptx:
                extension = ".pptx"
                detected_type = "PowerPoint"
            else:
                extension = ".unknown"
                detected_type = f"Unknown ({mime_type if mime_type else 'no magic'})"

            return {
                "is_valid": is_valid,
                "extension": extension,
                "detected_type": detected_type,
                "mime_type": mime_type,
                "size": file_size,
                "filename": filename,
            }

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            raise SourceError(f"File validation failed: {e}") from e

    async def _validate_document_format(self, file_path: str) -> dict[str, Any]:
        """Async wrapper for synchronous document validation."""
        import asyncio

        return await asyncio.to_thread(self._validate_document_format_sync, file_path)

    async def _check_media_availability(self, url: str) -> dict[str, Any]:
        """Check if URL has downloadable media using yt-dlp."""
        try:
            import yt_dlp

            probe_opts = {
                "quiet": True,
                "no_warnings": True,
                "nocheckcertificate": True,
                "nocookies": True,
            }

            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                return {
                    "has_media": False,
                    "error": "Could not retrieve media information",
                }

            # Check formats
            formats = info.get("formats", [])
            has_video = any(f.get("vcodec") and f["vcodec"] != "none" for f in formats)
            has_audio = any(f.get("acodec") and f["acodec"] != "none" for f in formats)

            return {
                "has_media": has_video or has_audio,
                "has_video": has_video,
                "has_audio": has_audio,
                "title": info.get("title", "media_download"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "description": info.get("description", ""),
                "view_count": info.get("view_count"),
                "upload_date": info.get("upload_date"),
            }

        except ImportError:
            return {"has_media": False, "error": "yt-dlp not available"}
        except Exception as e:
            self.logger.error(f"Media check error: {e}")
            return {"has_media": False, "error": str(e)}

    async def _download_video(
        self, url: str, temp_dir: str, base_filename: str
    ) -> Optional[str]:
        """Download video using yt-dlp."""
        try:
            import yt_dlp

            output_path = os.path.join(temp_dir, f"{base_filename}_video.%(ext)s")

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "outtmpl": output_path,
                "format": "bestvideo+bestaudio/best",
                "nocheckcertificate": True,
                "nocookies": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find downloaded file
            for file_path in Path(temp_dir).iterdir():
                if file_path.is_file() and base_filename in file_path.name:
                    self.logger.info(f"Downloaded video: {file_path}")
                    return str(file_path)

            return None

        except Exception as e:
            self.logger.error(f"Video download error: {e}")
            return None

    async def _download_audio(
        self, url: str, temp_dir: str, base_filename: str
    ) -> Optional[str]:
        """Download audio using yt-dlp."""
        try:
            import yt_dlp

            output_path = os.path.join(temp_dir, f"{base_filename}_audio.%(ext)s")

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "outtmpl": output_path,
                "format": "bestaudio/best",
                "nocheckcertificate": True,
                "nocookies": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find downloaded file
            for file_path in Path(temp_dir).iterdir():
                if file_path.is_file() and base_filename in file_path.name:
                    self.logger.info(f"Downloaded audio: {file_path}")
                    return str(file_path)

            return None

        except Exception as e:
            self.logger.error(f"Audio download error: {e}")
            return None

    async def _fetch_bilibili_media(self, url: str) -> UrlFetchResult:
        """Fetch media from Bilibili using bilix."""
        self.logger.info(f"Fetching Bilibili media: {url}")

        try:
            # Create temp directory (Note: cleanup is handled by orchestrator via temp_dirs list)
            temp_dir = tempfile.mkdtemp(prefix="deepsight_bilibili_")

            # Download video directly using bilix
            downloaded_path = await self._download_bilibili_video(url, temp_dir)

            if not downloaded_path:
                raise SourceError("Failed to download Bilibili video")

            # Get actual filename
            actual_filename = os.path.basename(downloaded_path)

            # Basic metadata
            metadata = {
                "has_media": True,
                "has_video": True,
                "has_audio": True,
                "platform": "bilibili",
                "title": Path(downloaded_path).stem,
            }

            return UrlFetchResult(
                fetch_type="media",
                local_path=downloaded_path,
                filename=actual_filename,
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error(f"Bilibili media fetch error: {e}")
            raise SourceError(f"Failed to fetch Bilibili media: {e}") from e

    async def _download_bilibili_video(self, url: str, temp_dir: str) -> Optional[str]:
        """Download Bilibili video using bilix."""
        try:
            from bilix.sites.bilibili import DownloaderBilibili

            # Download video to temp directory
            download_path = Path(temp_dir)

            async with DownloaderBilibili() as downloader:
                await downloader.get_video(url, path=download_path)

            # Find downloaded file
            for file_path in download_path.iterdir():
                if file_path.is_file() and file_path.suffix in [".mp4", ".flv", ".mkv"]:
                    self.logger.info(f"Downloaded Bilibili video: {file_path}")
                    return str(file_path)

            return None

        except ImportError:
            self.logger.error("bilix not available")
            raise SourceError("bilix library is required for Bilibili downloads")
        except Exception as e:
            self.logger.error(f"Bilibili video download error: {e}")
            raise

    async def _load_crawl4ai(self):
        """Lazy load crawl4ai."""
        if self._crawl4ai_loaded:
            return

        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
            from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
            from crawl4ai.content_filter_strategy import PruningContentFilter

            self._crawl4ai = AsyncWebCrawler
            self._crawl4ai_config = CrawlerRunConfig
            self._crawl4ai_gen = DefaultMarkdownGenerator
            self._crawl4ai_filter = PruningContentFilter
            self._crawl4ai_loaded = True
        except ImportError as e:
            self.logger.warning(f"crawl4ai not available: {e}")
            self._crawl4ai_loaded = False


