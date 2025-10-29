"""
PDF parser using MinerU API with PyMuPDF fallback.
"""

import base64
import json
import logging
import os
import tempfile
import time
from typing import Any, Optional

import requests

from ...utils.helpers import clean_title
from ..exceptions import ParseError
from .base_parser import BaseParser, ParseResult

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class PdfParser(BaseParser):
    """PDF parser with MinerU primary and PyMuPDF fallback."""

    def __init__(
        self,
        mineru_base_url: str,
        logger: Optional[logging.Logger] = None,
    ):
        # Normalize URL
        if not str(mineru_base_url).lower().startswith(("http://", "https://")):
            mineru_base_url = f"http://{mineru_base_url}"
        self.mineru_base_url = mineru_base_url.rstrip("/")
        self.mineru_parse_endpoint = f"{self.mineru_base_url}/file_parse"
        self.logger = logger or logging.getLogger(__name__)

    async def parse(self, file_path: str, metadata: dict[str, Any]) -> ParseResult:
        """
        Parse PDF file using MinerU, fallback to PyMuPDF on failure.

        Args:
            file_path: Path to PDF file
            metadata: File metadata (filename, extension, etc.)

        Returns:
            ParseResult with content, metadata, and optional marker_extraction_result
        """
        # Try MinerU first
        if self._check_mineru_health():
            try:
                return await self._parse_with_mineru(file_path, metadata)
            except Exception as e:
                self.logger.warning(
                    f"MinerU parsing failed: {e}, falling back to PyMuPDF"
                )

        # Fallback to PyMuPDF
        return await self._parse_with_pymupdf(file_path, metadata)

    def _check_mineru_health(self) -> bool:
        """Check if MinerU API is available."""
        try:
            response = requests.get(f"{self.mineru_base_url}/docs", timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"MinerU health check failed: {e}")
            return False

    async def _parse_with_mineru(
        self, file_path: str, metadata: dict[str, Any]
    ) -> ParseResult:
        """Parse PDF using MinerU API."""
        self.logger.info(f"Starting MinerU parsing of {file_path}")
        start_time = time.time()

        # Generate clean filename
        original_filename = metadata.get("filename", "document.pdf")
        base_title = (
            original_filename.rsplit(".", 1)[0]
            if "." in original_filename
            else original_filename
        )
        clean_pdf_title = clean_title(base_title)

        # Call MinerU API
        mineru_result = self._call_mineru_api(file_path)

        # Extract results
        results = mineru_result.get("results", {})
        if not results:
            raise ParseError("No results returned from MinerU API")

        # Get first document result
        doc_key = next(iter(results.keys()))
        doc_result = results[doc_key]

        # Extract markdown content and images
        md_content = doc_result.get("md_content", "")
        images = doc_result.get("images", {})

        # Save to temporary directory
        temp_dir = tempfile.mkdtemp(suffix="_mineru_output")

        # Save markdown content
        md_file_path = os.path.join(temp_dir, f"{doc_key}.md")
        with open(md_file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Save images
        image_files = []
        for img_name, img_data in images.items():
            if img_data.startswith("data:image/"):
                # Decode base64 images
                header, data = img_data.split(",", 1)
                img_bytes = base64.b64decode(data)

                img_path = os.path.join(temp_dir, img_name)
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                image_files.append(img_path)

        self.logger.info(
            f"Created {len(os.listdir(temp_dir))} files: "
            f"{[os.path.basename(f) for f in [md_file_path] + image_files]}"
        )

        # Get PDF metadata using PyMuPDF if available
        pdf_metadata = self._extract_pdf_metadata(file_path, mineru_result)
        pdf_metadata["has_mineru_extraction"] = True
        pdf_metadata["has_markdown_content"] = bool(md_content)

        # Calculate features
        features_available = ["advanced_pdf_extraction", "markdown_conversion"]
        if images:
            features_available.append("image_extraction")
        if "table" in md_content.lower() or "|" in md_content:
            features_available.append("table_extraction")
        if any(marker in md_content for marker in ["$$", "$", "\\("]):
            features_available.append("formula_extraction")
        features_available.append("layout_analysis")

        duration = time.time() - start_time
        self.logger.info(f"MinerU parsing completed in {duration:.2f} seconds")

        # Return result with marker extraction info
        return ParseResult(
            content="",  # Empty content since MinerU files contain everything
            metadata=pdf_metadata,
            features_available=features_available,
            marker_extraction_result={
                "success": True,
                "temp_marker_dir": temp_dir,
                "clean_title": clean_pdf_title,
            },
        )

    async def _parse_with_pymupdf(
        self, file_path: str, metadata: dict[str, Any]
    ) -> ParseResult:
        """Parse PDF using PyMuPDF fallback."""
        self.logger.info(f"Using PyMuPDF fallback for {file_path}")

        if not fitz:
            raise ParseError("PyMuPDF (fitz) is not available")

        doc = fitz.open(file_path)
        content = ""

        # Extract metadata
        pdf_metadata = {
            "page_count": doc.page_count,
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
            "modification_date": doc.metadata.get("modDate", ""),
            "processing_method": "pymupdf_fallback",
        }

        # Extract text from all pages
        for page_num in range(doc.page_count):
            page = doc[page_num]
            content += f"\n=== Page {page_num + 1} ===\n"
            page_text = page.get_text()
            content += page_text

        doc.close()

        # Check if extraction was successful
        if not content.strip():
            content = (
                f"PDF document '{metadata['filename']}' appears to be image-based or empty. "
                f"Text extraction may require OCR processing."
            )

        return ParseResult(
            content=content,
            metadata=pdf_metadata,
            features_available=[
                "advanced_pdf_extraction",
                "figure_extraction",
                "table_extraction",
            ],
        )

    def _call_mineru_api(self, file_path: str) -> dict[str, Any]:
        """Call MinerU API to parse PDF."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        try:
            # Prepare multipart form data
            files = {
                "files": (
                    os.path.basename(file_path),
                    open(file_path, "rb"),
                    "application/pdf",
                )
            }

            data = {
                "output_dir": "./output",
                "lang_list": ["ch"],
                "backend": "pipeline",
                "parse_method": "auto",
                "formula_enable": True,
                "table_enable": True,
                "server_url": "10.218.163.144",
                "return_md": True,
                "return_middle_json": False,
                "return_model_output": False,
                "return_content_list": False,
                "return_images": True,
                "response_format_zip": False,
                "start_page_id": 0,
                "end_page_id": 99999,
            }

            # Make API request
            response = requests.post(
                self.mineru_parse_endpoint,
                files=files,
                data=data,
                timeout=300,  # 5 minute timeout
            )

            # Close file handle
            files["files"][1].close()

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"MinerU API request failed: {e}")
            raise ParseError(f"MinerU API request failed: {e}") from e
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse MinerU API response: {e}")
            raise ParseError(f"Invalid JSON response from MinerU API: {e}") from e

    def _extract_pdf_metadata(
        self, file_path: str, mineru_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract PDF metadata using PyMuPDF if available."""
        try:
            if fitz:
                doc = fitz.open(file_path)
                metadata = {
                    "page_count": doc.page_count,
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "creation_date": doc.metadata.get("creationDate", ""),
                    "modification_date": doc.metadata.get("modDate", ""),
                    "processing_method": "mineru_api",
                    "api_version": mineru_result.get("version", "unknown"),
                    "backend": mineru_result.get("backend", "pipeline"),
                }
                doc.close()
                return metadata
            else:
                return {
                    "processing_method": "mineru_api",
                    "api_version": mineru_result.get("version", "unknown"),
                    "backend": mineru_result.get("backend", "pipeline"),
                }
        except Exception as e:
            self.logger.warning(f"Could not extract PDF metadata: {e}")
            return {
                "processing_method": "mineru_api",
                "api_version": mineru_result.get("version", "unknown"),
                "metadata_error": str(e),
            }
