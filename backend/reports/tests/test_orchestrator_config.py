import unittest
from unittest.mock import MagicMock, patch


class TestOrchestratorConfig(unittest.TestCase):
    def test_validate_configuration_settings_uses_settings_helpers(self):
        # Patch services to avoid heavy initialization during orchestrator init
        with (
            patch("reports.orchestrator.ReportGenerationService") as gen_svc,
            patch("reports.orchestrator.JobService") as job_svc,
        ):
            gen_svc.return_value = MagicMock()
            job_svc.return_value = MagicMock()

            from reports.orchestrator import ReportOrchestrator

            orch = ReportOrchestrator()

            config = {"model_provider": "openai", "retriever": "duckduckgo"}
            results = orch.validate_configuration_settings(config)

            # Keys from our settings-backed helper
            self.assertIn("openai_model", results)
            self.assertIn("duckduckgo_retriever", results)
