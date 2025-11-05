"""
Document parser using MinerU API for PDFs, Word, and PowerPoint files, with PyMuPDF fallback for PDFs.
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


class DocuParser(BaseParser):
    """Document parser with MinerU for PDFs, Word, PowerPoint and PyMuPDF fallback for PDFs."""

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

        # CSS for document conversion
        self.pptx_css = """
        @page {
            size: A4 landscape;
            margin: 1.5cm;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            break-inside: auto;
            font-size: 10pt;
        }
        tr {
            break-inside: avoid;
            page-break-inside: avoid;
        }
        td {
            border: 0.75pt solid #000;
            padding: 6pt;
        }
        img {
            max-width: 100%;
            height: auto;
            object-fit: contain;
        }
        """

        self.docx_css = """
        @page {
            size: A4;
            margin: 2cm;
        }
        img {
            max-width: 100%;
            max-height: 25cm;
            object-fit: contain;
            margin: 12pt auto;
        }
        div, p {
            max-width: 100%;
            word-break: break-word;
            font-size: 10pt;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            break-inside: auto;
            font-size: 10pt;
        }
        tr {
            break-inside: avoid;
            page-break-inside: avoid;
        }
        td {
            border: 0.75pt solid #000;
            padding: 6pt;
        }
        """

    def _convert_pptx_to_pdf(self, filepath: str) -> str:
        """Convert PPTX to PDF and return temp PDF path."""
        import base64
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
        from weasyprint import CSS, HTML

        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_pdf_path = temp_pdf.name
        temp_pdf.close()

        try:
            pptx = Presentation(filepath)
            html_parts = []

            for slide_index, slide in enumerate(pptx.slides):
                html_parts.append("<section>")

                # Process shapes in the slide
                for shape in slide.shapes:
                    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                        html_parts.append(self._handle_pptx_group(shape))
                        continue

                    if shape.has_table:
                        html_parts.append(self._handle_pptx_table(shape))
                        continue

                    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                        html_parts.append(self._handle_pptx_image(shape))
                        continue

                    if hasattr(shape, "text") and shape.text is not None:
                        if shape.has_text_frame:
                            html_parts.append(self._handle_pptx_text(shape))
                        else:
                            html_parts.append(f"<p>{self._escape_html(shape.text)}</p>")

                html_parts.append("</section>")

            html = "\n".join(html_parts)
            HTML(string=html).write_pdf(temp_pdf_path, stylesheets=[CSS(string=self.pptx_css)])

            return temp_pdf_path

        except Exception as e:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            raise ParseError(f"PPTX to PDF conversion failed: {e}") from e

    def _convert_docx_to_pdf(self, filepath: str) -> str:
        """Convert DOCX to PDF and return temp PDF path."""
        import re
        from io import BytesIO
        import mammoth
        from PIL import Image
        from weasyprint import CSS, HTML

        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_pdf_path = temp_pdf.name
        temp_pdf.close()

        try:
            with open(filepath, "rb") as docx_file:
                result = mammoth.convert_to_html(docx_file)
                html = result.value
                html = self._preprocess_base64_images(html)

                HTML(string=html).write_pdf(temp_pdf_path, stylesheets=[CSS(string=self.docx_css)])

            return temp_pdf_path

        except Exception as e:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            raise ParseError(f"DOCX to PDF conversion failed: {e}") from e

    def _handle_pptx_group(self, group_shape) -> str:
        """Recursively handle shapes in a group."""
        from pptx.enum.shapes import MSO_SHAPE_TYPE

        group_parts = []
        for shape in group_shape.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                group_parts.append(self._handle_pptx_group(shape))
                continue

            if shape.has_table:
                group_parts.append(self._handle_pptx_table(shape))
                continue

            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                group_parts.append(self._handle_pptx_image(shape))
                continue

            if hasattr(shape, "text"):
                if shape.has_text_frame:
                    group_parts.append(self._handle_pptx_text(shape))
                else:
                    group_parts.append(f"<p>{self._escape_html(shape.text)}</p>")

        return "".join(group_parts)

    def _handle_pptx_text(self, shape) -> str:
        """Process shape text including bullet/numbered lists."""
        from pptx.enum.shapes import PP_PLACEHOLDER

        label_html_tag = "p"
        if shape.is_placeholder:
            placeholder_type = shape.placeholder_format.type
            if placeholder_type in [PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE]:
                label_html_tag = "h3"
            elif placeholder_type == PP_PLACEHOLDER.SUBTITLE:
                label_html_tag = "h4"

        html_parts = []
        list_open = False
        list_type = None

        for paragraph in shape.text_frame.paragraphs:
            p_el = paragraph._element
            bullet_char = p_el.find(".//a:buChar", namespaces=p_el.nsmap)
            bullet_num = p_el.find(".//a:buAutoNum", namespaces=p_el.nsmap)

            is_bullet = (bullet_char is not None) or (paragraph.level > 0)
            is_numbered = bullet_num is not None

            if is_bullet or is_numbered:
                current_list_type = "ol" if is_numbered else "ul"
                if not list_open:
                    list_open = True
                    list_type = current_list_type
                    html_parts.append(f"<{list_type}>")
                elif list_open and list_type != current_list_type:
                    html_parts.append(f"</{list_type}>")
                    list_type = current_list_type
                    html_parts.append(f"<{list_type}>")

                p_text = "".join(run.text for run in paragraph.runs)
                if p_text:
                    html_parts.append(f"<li>{self._escape_html(p_text)}</li>")
            else:
                if list_open:
                    html_parts.append(f"</{list_type}>")
                    list_open = False
                    list_type = None

                p_text = "".join(run.text for run in paragraph.runs)
                if p_text:
                    html_parts.append(f"<{label_html_tag}>{self._escape_html(p_text)}</{label_html_tag}>")

        if list_open:
            html_parts.append(f"</{list_type}>")

        return "".join(html_parts)

    def _handle_pptx_image(self, shape) -> str:
        """Embed image as base64 in HTML."""
        import base64

        try:
            image = shape.image
            image_bytes = image.blob
            img_str = base64.b64encode(image_bytes).decode("utf-8")
            return f"<img src='data:{image.content_type};base64,{img_str}' />"
        except Exception as e:
            self.logger.warning(f"Warning: image cannot be loaded: {e}")
            return ""

    def _handle_pptx_table(self, shape) -> str:
        """Render table as HTML."""
        table_html = ["<table border='1'>"]

        for row in shape.table.rows:
            row_html = ["<tr>"]
            for cell in row.cells:
                row_html.append(f"<td>{self._escape_html(cell.text)}</td>")
            row_html.append("</tr>")
            table_html.append("".join(row_html))

        table_html.append("</table>")
        return "".join(table_html)

    def _preprocess_base64_images(self, html_content: str) -> str:
        """Preprocess base64 images in HTML."""
        import re
        import base64
        from io import BytesIO
        from PIL import Image

        pattern = r'data:([^;]+);base64,([^"\'>\s]+)'

        def convert_image(match):
            try:
                img_data = base64.b64decode(match.group(2))
                with BytesIO(img_data) as bio:
                    with Image.open(bio) as img:
                        output = BytesIO()
                        img.save(output, format=img.format)
                        new_base64 = base64.b64encode(output.getvalue()).decode()
                        return f"data:{match.group(1)};base64,{new_base64}"
            except Exception as e:
                self.logger.error(f"Failed to process image: {e}")
                return ""

        return re.sub(pattern, convert_image, html_content)

    def _escape_html(self, text: str) -> str:
        """Minimal escaping for HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    async def parse(self, file_path: str, metadata: dict[str, Any]) -> ParseResult:
        """
        Parse document file (PDF, Word, PowerPoint) using MinerU, with PyMuPDF fallback for PDFs.

        Args:
            file_path: Path to document file
            metadata: File metadata (filename, extension, etc.)

        Returns:
            ParseResult with content, metadata, and optional marker_extraction_result
        """
        file_extension = metadata.get("file_extension", "").lower()
        is_pdf = file_extension == ".pdf"
        is_word = file_extension in [".docx", ".doc"]
        is_powerpoint = file_extension in [".pptx", ".ppt"]

        # Try MinerU first
        if self._check_mineru_health():
            try:
                return await self._parse_with_mineru(file_path, metadata)
            except Exception as e:
                self.logger.warning(
                    f"MinerU parsing failed: {e}"
                )
                # Fall back based on file type
                if is_pdf:
                    self.logger.info("Falling back to PyMuPDF for PDF")
                elif is_word:
                    self.logger.info("Falling back to python-docx for Word document")
                elif is_powerpoint:
                    self.logger.info("Falling back to python-pptx for PowerPoint")
                else:
                    raise ParseError(f"MinerU parsing failed for {file_extension} file: {e}")

        # Apply appropriate fallback
        if is_pdf:
            return await self._parse_with_pymupdf(file_path, metadata)
        elif is_word:
            return await self._parse_with_docx(file_path, metadata)
        elif is_powerpoint:
            return await self._parse_with_pptx(file_path, metadata)
        else:
            raise ParseError(f"MinerU service is unavailable and no fallback exists for {file_extension} files")

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
        """Parse document (PDF, Word, PowerPoint) using MinerU API."""
        file_extension = metadata.get("file_extension", "").lower()

        # Determine file type for logging
        file_type_map = {
            ".pdf": "PDF",
            ".docx": "Word",
            ".doc": "Word",
            ".pptx": "PowerPoint",
            ".ppt": "PowerPoint",
        }
        file_type = file_type_map.get(file_extension, "Document")
        self.logger.info(f"Starting MinerU parsing of {file_type} file: {file_path}")
        start_time = time.time()

        # Convert PPTX/DOCX to PDF if needed
        temp_pdf_path = None
        actual_file_path = file_path

        try:
            if file_extension in [".pptx", ".ppt"]:
                self.logger.info(f"Converting {file_type} to PDF for MinerU processing")
                temp_pdf_path = self._convert_pptx_to_pdf(file_path)
                actual_file_path = temp_pdf_path
            elif file_extension in [".docx", ".doc"]:
                self.logger.info(f"Converting {file_type} to PDF for MinerU processing")
                temp_pdf_path = self._convert_docx_to_pdf(file_path)
                actual_file_path = temp_pdf_path

            # Generate clean filename
            default_filename = f"document{file_extension}" if file_extension else "document.pdf"
            original_filename = metadata.get("filename", default_filename)
            base_title = (
                original_filename.rsplit(".", 1)[0]
                if "." in original_filename
                else original_filename
            )
            clean_pdf_title = clean_title(base_title)

            # Call MinerU API with the actual file (original PDF or converted PDF)
            mineru_result = self._call_mineru_api(actual_file_path)

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

            # Get document metadata
            doc_metadata = self._extract_document_metadata(file_path, metadata, mineru_result)
            doc_metadata["has_mineru_extraction"] = True
            doc_metadata["has_markdown_content"] = bool(md_content)
            doc_metadata["file_type"] = file_type.lower()

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
                metadata=doc_metadata,
                features_available=features_available,
                marker_extraction_result={
                    "success": True,
                    "temp_marker_dir": temp_dir,
                    "clean_title": clean_pdf_title,
                },
            )

        finally:
            # Clean up temporary PDF file if it was created
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                try:
                    os.remove(temp_pdf_path)
                    self.logger.debug(f"Cleaned up temporary PDF: {temp_pdf_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary PDF: {e}")

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

    async def _parse_with_docx(
        self, file_path: str, metadata: dict[str, Any]
    ) -> ParseResult:
        """Parse Word document using python-docx fallback."""
        self.logger.info(f"Using python-docx fallback for {file_path}")

        try:
            # Try python-docx for .docx files
            if metadata.get("file_extension", "").lower() == ".docx":
                try:
                    from docx import Document

                    doc = Document(file_path)
                    content = "\n\n".join(
                        [para.text for para in doc.paragraphs if para.text]
                    )

                    doc_metadata = {
                        "processing_method": "python_docx_fallback",
                        "paragraph_count": len(doc.paragraphs),
                        "word_count": len(content.split()),
                    }

                    return ParseResult(
                        content=content,
                        metadata=doc_metadata,
                        features_available=["text_extraction", "document_structure"],
                    )
                except ImportError:
                    self.logger.warning(
                        "python-docx not available, returning placeholder"
                    )

            # Fallback: return a message that file is uploaded but needs processing
            content = (
                f"Word document '{metadata['filename']}' uploaded successfully. "
                f"Text extraction requires python-docx installation for detailed processing."
            )

            return ParseResult(
                content=content,
                metadata={
                    "file_type": "word_document",
                    "supported_extraction": False,
                    "processing_method": "fallback_placeholder",
                },
                features_available=["text_extraction", "formatting_preservation"],
            )

        except Exception as e:
            raise ParseError(f"Word document fallback processing failed: {e}") from e

    async def _parse_with_pptx(
        self, file_path: str, metadata: dict[str, Any]
    ) -> ParseResult:
        """Parse PowerPoint presentation using python-pptx fallback."""
        self.logger.info(f"Using python-pptx fallback for {file_path}")

        try:
            # Try python-pptx for extraction
            try:
                from pptx import Presentation

                prs = Presentation(file_path)

                content = ""
                for i, slide in enumerate(prs.slides):
                    content += f"\n=== Slide {i + 1} ===\n"
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text:
                            content += shape.text + "\n"

                ppt_metadata = {
                    "processing_method": "python_pptx_fallback",
                    "slide_count": len(prs.slides),
                    "word_count": len(content.split()),
                }

                return ParseResult(
                    content=content,
                    metadata=ppt_metadata,
                    features_available=["text_extraction", "slide_structure"],
                )

            except ImportError:
                self.logger.warning(
                    "python-pptx not available, returning placeholder"
                )
                # Fallback
                content = (
                    f"Presentation '{metadata['filename']}' uploaded successfully. "
                    f"Text extraction requires python-pptx installation for detailed processing."
                )

                return ParseResult(
                    content=content,
                    metadata={
                        "file_type": "presentation",
                        "supported_extraction": False,
                        "processing_method": "fallback_placeholder",
                    },
                    features_available=[
                        "slide_extraction",
                        "text_extraction",
                        "image_extraction",
                    ],
                )

        except Exception as e:
            raise ParseError(f"Presentation fallback processing failed: {e}") from e

    def _call_mineru_api(self, file_path: str) -> dict[str, Any]:
        """Call MinerU API to parse document (PDF, Word, PowerPoint)."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")

        try:
            # Detect file type and set appropriate MIME type
            file_extension = os.path.splitext(file_path)[1].lower()
            mime_type_map = {
                ".pdf": "application/pdf",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".doc": "application/msword",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".ppt": "application/vnd.ms-powerpoint",
            }
            mime_type = mime_type_map.get(file_extension, "application/octet-stream")

            # Prepare multipart form data
            files = {
                "files": (
                    os.path.basename(file_path),
                    open(file_path, "rb"),
                    mime_type,
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

    def _extract_document_metadata(
        self, file_path: str, metadata: dict[str, Any], mineru_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract document metadata (PDF, Word, PowerPoint)."""
        file_extension = metadata.get("file_extension", "").lower()
        is_pdf = file_extension == ".pdf"

        base_metadata = {
            "processing_method": "mineru_api",
            "api_version": mineru_result.get("version", "unknown"),
            "backend": mineru_result.get("backend", "pipeline"),
        }

        # For PDF files, try to extract additional metadata using PyMuPDF
        if is_pdf:
            try:
                if fitz:
                    doc = fitz.open(file_path)
                    base_metadata.update({
                        "page_count": doc.page_count,
                        "title": doc.metadata.get("title", ""),
                        "author": doc.metadata.get("author", ""),
                        "creation_date": doc.metadata.get("creationDate", ""),
                        "modification_date": doc.metadata.get("modDate", ""),
                    })
                    doc.close()
            except Exception as e:
                self.logger.warning(f"Could not extract PDF metadata: {e}")
                base_metadata["metadata_error"] = str(e)

        return base_metadata
