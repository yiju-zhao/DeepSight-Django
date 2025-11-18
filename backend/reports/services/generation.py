"""
ReportGenerationService: streamlined high-level generation flow.
Implements orchestration without legacy indirection.
"""

import logging
import shutil
from pathlib import Path
from typing import Any

from ..models import Report
from ..storage import StorageFactory
from .config import (
    get_free_retrievers,
    get_model_provider_config,
    get_retriever_config,
    get_search_depth_options,
    get_supported_providers,
    get_supported_retrievers,
    get_time_range_mapping,
)
from .input_processor import KnowledgeBaseInputProcessor

logger = logging.getLogger(__name__)


class ReportGenerationService:
    def __init__(self):
        self._generator = None
        self.input_processor = KnowledgeBaseInputProcessor()
        self.file_storage = StorageFactory.create_storage()
        self._temp_dirs = []

    @property
    def generator(self):
        """Lazy-load the DeepReportGenerator."""
        if self._generator is None:
            try:
                from agents.report_agent.deep_report_generator import (
                    DeepReportGenerator,
                )

                self._generator = DeepReportGenerator()
            except ImportError as e:
                raise ImportError(f"Failed to import DeepReportGenerator: {e}")
            except Exception as e:
                raise Exception(f"Failed to initialize DeepReportGenerator: {e}")
        return self._generator

    def generate_report(self, report_id: int) -> dict[str, Any]:
        try:
            try:
                report = Report.objects.get(id=report_id)
            except Report.DoesNotExist:
                error_msg = f"Report {report_id} not found"
                logger.error(error_msg)
                raise Exception(error_msg)

            logger.info(f"Starting report generation for report {report_id}")

            if report.include_image:
                try:
                    from .job import JobService

                    job_service = JobService()
                    if not job_service.prepare_report_images(report):
                        logger.warning(
                            f"Failed to prepare ReportImage records for report {report_id}, continuing anyway"
                        )
                except Exception as e:
                    logger.warning(
                        f"Image preparation error for report {report_id}: {e}"
                    )

            output_dir = self.file_storage.create_output_directory(
                user_id=report.user.pk,
                report_id=str(report.id),
                notebook_id=report.notebooks.pk if report.notebooks else None,
            )
            logger.info(f"Output directory for report {report_id}: {output_dir}")

            content_data = {}
            if report.source_ids:
                processed_data = self.input_processor.process_selected_files(
                    report.source_ids, user_id=report.user.pk
                )
                content_data = self.input_processor.get_content_data(processed_data)

                if report.include_image:
                    from .image import ImageService

                    selected_file_ids = content_data.get("selected_file_ids", [])
                    if selected_file_ids:
                        image_service = ImageService()
                        image_service.create_combined_figure_data(
                            report, selected_file_ids
                        )

            figure_data = []
            if report.include_image and hasattr(report, "_cached_figure_data"):
                figure_data = report._cached_figure_data

            # Parse custom requirements if provided
            if report.custom_requirements and not report.parsed_requirements:
                try:
                    from .requirements_parser import RequirementsParser

                    parser = RequirementsParser(model_provider=report.model_provider)
                    parsed = parser.parse(report.custom_requirements)

                    if parsed:
                        report.parsed_requirements = parsed
                        report.save(update_fields=["parsed_requirements"])
                        logger.info(
                            f"Parsed custom requirements for report {report_id}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to parse custom requirements: {e}. Continuing without parsing."
                    )

            config_dict = report.get_configuration_dict()
            config_dict.update(
                {
                    "output_dir": output_dir,
                    "old_outline": report.old_outline,
                    "report_id": str(report.id),
                    "user_id": str(report.user.pk),
                    "figure_data": figure_data,
                    **content_data,
                }
            )

            if not self.validate_configuration(config_dict):
                raise Exception("Invalid configuration for report generation")

            result = self._generate_report(config_dict)
            if not result.get("success", False):
                error_msg = result.get("error_message", "Report generation failed")
                raise Exception(error_msg)

            generated_files = result.get("generated_files", [])
            stored_files = generated_files
            main_report_file = self.file_storage.get_main_report_file(stored_files)

            final_result = {
                "success": True,
                "report_id": report.id,
                "article_title": result.get("article_title", report.article_title),
                "output_directory": str(output_dir),
                "generated_files": stored_files,
                "main_report_file": main_report_file,
                "processing_logs": result.get("processing_logs", []),
                "report_content": result.get("report_content", ""),
                "created_at": result.get("created_at", ""),
                "generated_topic": result.get("generated_topic", ""),
            }

            logger.info(
                f"Report generation completed successfully for report {report_id}"
            )
            return final_result
        except Exception as e:
            logger.error(f"Error in report generation for report {report_id}: {e}")
            try:
                self.cancel_generation(str(report_id) if report else "unknown")
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to cleanup temp directories after error: {cleanup_error}"
                )
            raise

    def validate_configuration(self, config: dict[str, Any]) -> bool:
        """Validate report generation configuration."""
        try:
            logger.info(f"Validating report configuration: {config}")

            topic = config.get("topic", "").strip()
            source_ids = config.get("source_ids", [])
            article_title = config.get("article_title", "").strip()
            output_dir = config.get("output_dir")

            if not topic and not source_ids:
                logger.error("Must provide either topic or source_ids")
                return False

            if not article_title:
                if topic:
                    article_title = topic
                    config["article_title"] = article_title
                    logger.info(f"Using topic as article_title: {article_title}")
                else:
                    article_title = "Research Report"
                    config["article_title"] = article_title
                    logger.info(f"Using default article_title: {article_title}")

            if not output_dir:
                logger.error(f"Missing or empty output_dir: {output_dir}")
                return False

            provider = config.get("model_provider", "openai")
            provider_config = get_model_provider_config(provider)
            logger.info(
                f"Model provider '{provider}' config: api_key={'***' if provider_config.get('api_key') else 'MISSING'}"
            )
            if not provider_config.get("api_key"):
                logger.error(f"Missing API key for model provider: {provider}")
                return False

            retriever = config.get("retriever", "tavily")
            retriever_config = get_retriever_config(retriever)
            logger.info(
                f"Retriever '{retriever}' config: api_key={'***' if retriever_config.get('api_key') else 'MISSING'}"
            )
            requires_api_key = retriever not in get_free_retrievers()
            if requires_api_key and not retriever_config.get("api_key"):
                logger.error(f"Missing API key for retriever: {retriever}")
                return False

            logger.info("Report configuration validation passed")
            return True
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            return False

    def _generate_report(self, config: dict[str, Any]) -> dict[str, Any]:
        """Generate report using the core generator."""
        try:
            from agents.report_agent.deep_report_generator import ReportGenerationConfig

            deep_config = ReportGenerationConfig.from_dict(config)
            result = self.generator.generate_report(deep_config)

            if not result.success:
                return {
                    "success": False,
                    "error_message": result.error_message or "Report generation failed",
                }

            generated_files = result.generated_files or []
            return {
                "success": True,
                "article_title": result.article_title,
                "generated_topic": getattr(result, "generated_topic", None),
                "report_content": getattr(result, "report_content", ""),
                "generated_files": generated_files,
                "processing_logs": result.processing_logs or [],
                "error_message": None,
            }
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                "success": False,
                "error_message": f"Report generation failed: {str(e)}",
            }

    def validate_report_config(self, config: dict[str, Any]) -> bool:
        """Public wrapper for validate_configuration."""
        try:
            return self.validate_configuration(config)
        except Exception as e:
            logger.error(f"Error validating report config: {e}")
            return False

    def get_supported_options(self) -> dict[str, Any]:
        """Get supported providers and configuration options."""
        try:
            return {
                "model_providers": get_supported_providers(),
                "retrievers": get_supported_retrievers(),
                "free_retrievers": get_free_retrievers(),
                "time_ranges": list(get_time_range_mapping().keys()),
                "search_depths": get_search_depth_options(),
            }
        except Exception as e:
            logger.error(f"Error getting supported options: {e}")
            return {}

    def cancel_generation(self, report_id: str) -> bool:
        """Cancel report generation and cleanup temp directories."""
        try:
            self._cleanup_all_temp_directories()
            logger.info(f"Cleaned up temp directories for cancelled report {report_id}")
            return True
        except Exception as e:
            logger.error(
                f"Error during cancellation cleanup for report {report_id}: {e}"
            )
            return False

    def _cleanup_temp_directory(self, temp_dir: str) -> None:
        """Cleanup a single temporary directory."""
        try:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
                if temp_dir in self._temp_dirs:
                    self._temp_dirs.remove(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")

    def _cleanup_all_temp_directories(self) -> None:
        """Cleanup all tracked temporary directories."""
        for temp_dir in self._temp_dirs.copy():
            self._cleanup_temp_directory(temp_dir)

    def __del__(self):
        """Cleanup on service deletion."""
        self._cleanup_all_temp_directories()


__all__ = ["ReportGenerationService"]
