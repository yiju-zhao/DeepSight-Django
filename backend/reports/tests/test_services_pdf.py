import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class FakeMarkdownPdf:
    def __init__(self, toc_level=0, optimize=True):
        self.meta = {}
        self.sections = []
        self._saved_path = None

    def add_section(self, section, user_css=None):
        self.sections.append((section, user_css))

    def save(self, output_path: str):
        # Simulate writing a PDF file by creating an empty file
        Path(output_path).write_bytes(b"%PDF-FAKE")
        self._saved_path = output_path


class FakeSection:
    def __init__(self, content, root=None, paper_size=None):
        self.content = content
        self.root = root
        self.paper_size = paper_size


class TestPdfService(unittest.TestCase):
    @patch("reports.services.pdf.requests.get")
    @patch("reports.services.pdf.Section", new=FakeSection)
    @patch("reports.services.pdf.MarkdownPdf", new=FakeMarkdownPdf)
    def test_convert_markdown_to_pdf_with_remote_image(self, mock_get):
        # Mock requests.get to return an image payload
        resp = Mock()
        resp.content = b"img-bytes"
        resp.headers = {"content-type": "image/png"}
        resp.raise_for_status = Mock()
        mock_get.return_value = resp

        from reports.services.pdf import PdfService

        svc = PdfService()
        md = '<h1>Title</h1>\n<img src="http://example.com/x.png">'
        out = Path("/tmp/test_report.pdf")
        try:
            pdf_path = svc.convert_markdown_to_pdf(md, str(out))
            self.assertTrue(Path(pdf_path).exists())
            # File contains our fake PDF header
            self.assertEqual(Path(pdf_path).read_bytes()[:4], b"%PDF")
        finally:
            if out.exists():
                out.unlink()
