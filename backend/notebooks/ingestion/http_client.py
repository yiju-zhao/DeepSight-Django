"""
Unified HTTP client with timeout and security features.
"""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
from urllib.parse import urlparse

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import requests  # Fallback to requests

from .exceptions import SourceError
from .url_security import sanitize_filename, validate_url_security

logger = logging.getLogger(__name__)


class SecureHttpClient:
    """
    Secure HTTP client with SSRF protection and timeout handling.
    """

    def __init__(
        self,
        connect_timeout: int = 30,
        read_timeout: int = 300,
        allow_private_networks: bool = False,
    ):
        """
        Initialize HTTP client.

        Args:
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            allow_private_networks: Allow private/internal IP addresses
        """
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.allow_private_networks = allow_private_networks

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        }

    def validate_url(self, url: str) -> None:
        """
        Validate URL for security issues.

        Raises:
            SourceError: If URL is unsafe
        """
        is_valid, error_msg = validate_url_security(url, self.allow_private_networks)
        if not is_valid:
            raise SourceError(f"Unsafe URL blocked: {error_msg}")

    def extract_filename_from_url(self, url: str, headers: dict) -> str:
        """
        Extract filename from URL or Content-Disposition header.

        Args:
            url: Request URL
            headers: Response headers

        Returns:
            Sanitized filename
        """
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
            filename = Path(parsed.path).name or "document"

        return sanitize_filename(filename)

    def download_file_sync(
        self, url: str, temp_dir: Optional[TemporaryDirectory] = None
    ) -> tuple[str, dict]:
        """
        Download file synchronously using httpx or requests.

        Args:
            url: URL to download
            temp_dir: Optional TemporaryDirectory to use

        Returns:
            (file_path, metadata) tuple where metadata contains:
                - content_type: Content-Type header
                - filename: Extracted filename
                - size: File size in bytes

        Raises:
            SourceError: If download fails
        """
        # Validate URL security
        self.validate_url(url)

        own_temp_dir = False
        if temp_dir is None:
            temp_dir = TemporaryDirectory(prefix="deepsight_download_")
            own_temp_dir = True

        temp_path = Path(temp_dir.name)

        try:
            logger.info(f"Downloading file from: {url}")

            if HTTPX_AVAILABLE:
                # Use httpx (preferred)
                timeout = httpx.Timeout(
                    connect=self.connect_timeout,
                    read=self.read_timeout,
                    write=30,
                    pool=10,
                )

                with httpx.Client(
                    timeout=timeout, headers=self.headers, follow_redirects=True
                ) as client:
                    with client.stream("GET", url) as response:
                        if response.status_code != 200:
                            raise SourceError(
                                f"Failed to download: HTTP {response.status_code}"
                            )

                        # Extract filename
                        filename = self.extract_filename_from_url(
                            url, dict(response.headers)
                        )
                        file_path = temp_path / filename

                        # Stream to file
                        total_bytes = 0
                        with open(file_path, "wb") as f:
                            for chunk in response.iter_bytes(chunk_size=8192):
                                f.write(chunk)
                                total_bytes += len(chunk)

                        content_type = response.headers.get("content-type", "").lower()

            else:
                # Fallback to requests
                timeout = (self.connect_timeout, self.read_timeout)

                response = requests.get(
                    url,
                    stream=True,
                    timeout=timeout,
                    headers=self.headers,
                    allow_redirects=True,
                )

                if response.status_code != 200:
                    raise SourceError(
                        f"Failed to download: HTTP {response.status_code}"
                    )

                # Extract filename
                filename = self.extract_filename_from_url(url, response.headers)
                file_path = temp_path / filename

                # Stream to file
                total_bytes = 0
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            total_bytes += len(chunk)

                content_type = response.headers.get("content-type", "").lower()

            logger.info(f"Downloaded {total_bytes} bytes to {file_path}")

            metadata = {
                "content_type": content_type,
                "filename": filename,
                "size": total_bytes,
            }

            return str(file_path), metadata

        except (TimeoutError, Exception) as e:
            if own_temp_dir:
                temp_dir.cleanup()
            logger.error(f"Download error: {e}")
            raise SourceError(f"Failed to download file: {e}") from e

    async def download_file(
        self, url: str, temp_dir: Optional[TemporaryDirectory] = None
    ) -> tuple[str, dict]:
        """
        Async wrapper for download_file_sync.

        Args:
            url: URL to download
            temp_dir: Optional TemporaryDirectory to use

        Returns:
            (file_path, metadata) tuple
        """
        import asyncio

        return await asyncio.to_thread(self.download_file_sync, url, temp_dir)
