"""
URL Fetcher - Unified URL fetching with webpage/document/media support.
"""

import logging
import mimetypes
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional
from urllib.parse import urlparse

import aiofiles
import aiohttp
import magic

from ..utils.helpers import clean_title
from .exceptions import SourceError


@dataclass
class UrlFetchResult:
    """Unified URL fetch result."""

    fetch_type: Literal["webpage", "document", "media"]
    content: Optional[str] = None  # For webpage content
    local_path: Optional[str] = None  # For downloaded files
    filename: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class UrlFetcher:
    """Unified URL fetcher combining webpage, document, and media fetching."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._crawl4ai_loaded = False
        self._crawl4ai = None

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
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
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
            async with self._crawl4ai(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    wait_for=2,
                    bypass_cache=True,
                    word_count_threshold=10,
                    remove_overlay_elements=True,
                    screenshot=False,
                    process_iframes=False,
                    exclude_tags=["nav", "header", "footer", "aside"],
                    exclude_external_links=True,
                    only_text=False,
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
                content = result.markdown or result.cleaned_html or ""

                # Clean content
                content = self._clean_markdown_content(content)

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

            # Create temp directory
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

    async def _download_to_temp(self, url: str) -> str:
        """Download file from URL to temporary location."""
        try:
            temp_dir = tempfile.mkdtemp()
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path) or "document"

            temp_file_path = os.path.join(temp_dir, filename)

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise SourceError(f"Failed to download: HTTP {response.status}")

                    content_type = response.headers.get("content-type", "").lower()

                    async with aiofiles.open(temp_file_path, "wb") as temp_file:
                        async for chunk in response.content.iter_chunked(8192):
                            await temp_file.write(chunk)

            # Fix extension based on content
            corrected_path = await self._fix_file_extension(
                temp_file_path, content_type
            )

            self.logger.info(
                f"Downloaded {os.path.getsize(corrected_path)} bytes to {corrected_path}"
            )
            return corrected_path

        except Exception as e:
            self.logger.error(f"Download error: {e}")
            raise SourceError(f"Failed to download file: {e}") from e

    async def _fix_file_extension(self, file_path: str, content_type: str) -> str:
        """Fix file extension based on content type or magic detection."""
        import shutil

        try:
            # Detect actual file type
            mime_type = magic.from_file(file_path, mime=True)

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

    async def _validate_document_format(self, file_path: str) -> dict[str, Any]:
        """Validate document file format."""
        try:
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)

            # Detect file type
            mime_type = magic.from_file(file_path, mime=True)
            file_type = magic.from_file(file_path)

            self.logger.info(
                f"Validating: {filename}, MIME: {mime_type}, Type: {file_type}"
            )

            # Check if valid
            is_pdf = mime_type == "application/pdf" or "PDF" in file_type
            is_pptx = (
                mime_type
                in [
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                ]
                or "PowerPoint" in file_type
                or "Microsoft Office" in file_type
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
                detected_type = f"Unknown ({mime_type})"

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
            # Create temp directory
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

    async def _download_bilibili_video(
        self, url: str, temp_dir: str
    ) -> Optional[str]:
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
            from crawl4ai import AsyncWebCrawler

            self._crawl4ai = AsyncWebCrawler
            self._crawl4ai_loaded = True
        except ImportError as e:
            self.logger.warning(f"crawl4ai not available: {e}")
            self._crawl4ai_loaded = False

    def _clean_markdown_content(self, content: str) -> str:
        """Clean markdown content by removing invalid image references."""
        if not content:
            return content

        # Remove broken image references
        content = re.sub(r"!\[.*?\]\([^)]*_page_\d+_Figure_\d+\.[^)]+\)", "", content)
        content = re.sub(
            r"!\[.*?\]\([^)]*\.(jpg|jpeg|png|gif|svg|webp)(?:\?[^)]*)?\)",
            lambda m: "" if not m.group(0).startswith("![](http") else m.group(0),
            content,
            flags=re.IGNORECASE,
        )

        # Clean up multiple newlines
        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

        return content.strip()
