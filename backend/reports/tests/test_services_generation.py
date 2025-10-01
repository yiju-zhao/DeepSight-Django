import unittest
from unittest.mock import patch, MagicMock


class TestReportGenerationService(unittest.TestCase):
    def test_generate_report_flow(self):
        with patch("reports.services.generation.Report") as ReportModel, \
             patch("reports.services.generation.DeepReportGeneratorAdapter") as Gen, \
             patch("reports.services.generation.KnowledgeBaseInputProcessor") as IP, \
             patch("reports.services.generation.StorageFactory") as SF:

            fake_report = MagicMock()
            fake_report.include_image = False
            fake_report.selected_files_paths = []
            fake_report.user.pk = 1
            fake_report.notebooks = None
            fake_report.id = 42
            fake_report.old_outline = ""
            fake_report.article_title = "Title"
            fake_report.get_configuration_dict.return_value = {}
            ReportModel.objects.get.return_value = fake_report

            storage = MagicMock()
            storage.create_output_directory.return_value = "/tmp/out"
            storage.get_main_report_file.return_value = "file.md"
            SF.create_storage.return_value = storage

            gen = MagicMock()
            gen.validate_configuration.return_value = True
            gen.generate_report.return_value = {
                "success": True,
                "article_title": "Title",
                "generated_files": ["file.md"],
                "processing_logs": [],
                "report_content": "body",
                "created_at": "",
                "generated_topic": "",
            }
            Gen.return_value = gen
            IP.return_value = MagicMock()

            from reports.services.generation import ReportGenerationService

            svc = ReportGenerationService()
            result = svc.generate_report(123)
            self.assertTrue(result.get("success"))
            storage.create_output_directory.assert_called_once()
            gen.generate_report.assert_called_once()

    def test_validate_and_supported_options_passthrough(self):
        with patch("reports.services.generation.DeepReportGeneratorAdapter") as Gen, \
             patch("reports.services.generation.KnowledgeBaseInputProcessor"), \
             patch("reports.services.generation.StorageFactory"):

            gen = MagicMock()
            gen.validate_configuration.return_value = True
            gen.get_supported_providers.return_value = {"model_providers": ["openai"]}
            Gen.return_value = gen

            from reports.services.generation import ReportGenerationService

            svc = ReportGenerationService()
            self.assertTrue(svc.validate_report_config({}))
            self.assertIn("model_providers", svc.get_supported_options())
