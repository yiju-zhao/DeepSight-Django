import unittest
from unittest.mock import patch


class TestImageServiceInsertion(unittest.TestCase):
    def test_insert_figure_images_replaces_placeholders(self):
        # Lazy import to ensure project paths are set by test runner
        from reports.services.image import ImageService

        # Create deterministic UUID and content with placeholder on its own line
        figure_id = "123e4567-e89b-12d3-a456-426614174000"
        content = f"Intro text\n\n<{figure_id}>\n\nOutro text"

        # Minimal fake ReportImage-like objects
        class _Report:
            id = "rpt-1"

        class _ReportImage:
            def __init__(self, fid, caption):
                self.figure_id = fid
                self.image_caption = caption
                self.report = _Report()

        report_images = [_ReportImage(figure_id, "Figure 1: Example")] 

        # Patch DatabaseUrlProvider to avoid DB access and return a stable URL
        with patch("reports.services.image.DatabaseUrlProvider.get_image_url", return_value="https://cdn.example/img.png"):
            svc = ImageService()
            updated = svc.insert_figure_images(content, report_images, report_id="rpt-1")

        # Ensure placeholder is replaced with an <img ...> and caption present
        self.assertIn("<img src=\"https://cdn.example/img.png\"", updated)
        self.assertNotIn(f"<{figure_id}>", updated)
        self.assertIn("Figure 1: Example", updated)

