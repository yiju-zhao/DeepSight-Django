import unittest
from unittest.mock import MagicMock, patch


class TestReportGenerationService(unittest.TestCase):
    def test_generate_report_flow(self):
        with (
            patch("reports.services.generation.Report") as ReportModel,
            patch(
                "agents.report_agent.deep_report_generator.DeepReportGenerator"
            ) as Gen,
            patch("reports.services.generation.KnowledgeBaseInputProcessor") as IP,
            patch("reports.services.generation.StorageFactory") as SF,
        ):
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
            result_obj = MagicMock()
            result_obj.success = True
            result_obj.article_title = "Title"
            result_obj.generated_files = ["file.md"]
            result_obj.processing_logs = []
            result_obj.report_content = "body"
            result_obj.generated_topic = ""
            gen.generate_report.return_value = result_obj
            Gen.return_value = gen
            IP.return_value = MagicMock()

            from reports.services.generation import ReportGenerationService

            with (
                patch("reports.services.generation.get_model_provider_config") as gmp,
                patch("reports.services.generation.get_retriever_config") as grc,
                patch("reports.services.generation.get_free_retrievers") as gfr,
            ):
                gmp.return_value = {"api_key": "test"}
                grc.return_value = {"api_key": "test"}
                gfr.return_value = []

                svc = ReportGenerationService()
                result = svc.generate_report(123)
                self.assertTrue(result.get("success"))
                storage.create_output_directory.assert_called_once()
                gen.generate_report.assert_called_once()

    def test_validate_and_supported_options_passthrough(self):
        with (
            patch(
                "agents.report_agent.deep_report_generator.DeepReportGenerator"
            ) as Gen,
            patch("reports.services.generation.KnowledgeBaseInputProcessor"),
            patch("reports.services.generation.StorageFactory"),
        ):
            gen = MagicMock()
            Gen.return_value = gen

            from reports.services.generation import ReportGenerationService

            with (
                patch("reports.services.generation.get_model_provider_config") as gmp,
                patch("reports.services.generation.get_retriever_config") as grc,
                patch("reports.services.generation.get_free_retrievers") as gfr,
                patch("reports.services.generation.get_supported_providers") as gsp,
                patch("reports.services.generation.get_supported_retrievers") as gsr,
                patch("reports.services.generation.get_time_range_mapping") as gtrm,
                patch("reports.services.generation.get_search_depth_options") as gsdo,
            ):
                gmp.return_value = {"api_key": "test"}
                grc.return_value = {"api_key": "test"}
                gfr.return_value = []
                gsp.return_value = ["openai"]
                gsr.return_value = ["tavily"]
                gtrm.return_value = {"day": 1}
                gsdo.return_value = ["basic", "advanced"]

                svc = ReportGenerationService()
                self.assertTrue(
                    svc.validate_report_config({"topic": "test", "output_dir": "/tmp"})
                )
                options = svc.get_supported_options()
                self.assertIn("model_providers", options)
