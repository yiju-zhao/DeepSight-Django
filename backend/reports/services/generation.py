"""
ReportGenerationService: streamlined high-level generation flow.
Implements orchestration without legacy indirection.
"""

import logging
from typing import Dict, Any

from .report_generator import DeepReportGeneratorAdapter
from .input_processor import KnowledgeBaseInputProcessor
from ..storage import StorageFactory
from ..models import Report

logger = logging.getLogger(__name__)


class ReportGenerationService:
    def __init__(self):
        self.report_generator = DeepReportGeneratorAdapter()
        self.input_processor = KnowledgeBaseInputProcessor()
        self.file_storage = StorageFactory.create_storage()

    def generate_report(self, report_id: int) -> Dict[str, Any]:
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
                    logger.warning(f"Image preparation error for report {report_id}: {e}")

            output_dir = self.file_storage.create_output_directory(
                user_id=report.user.pk,
                report_id=str(report.id),
                notebook_id=report.notebooks.pk if report.notebooks else None,
            )
            logger.info(f"Output directory for report {report_id}: {output_dir}")

            content_data = {}
            if report.selected_files_paths:
                processed_data = self.input_processor.process_selected_files(
                    report.selected_files_paths, user_id=report.user.pk
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

            if not self.report_generator.validate_configuration(config_dict):
                raise Exception("Invalid configuration for report generation")

            result = self.report_generator.generate_report(config_dict)
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
                self.report_generator.cancel_generation(str(report_id) if report else "unknown")
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to cleanup temp directories after error: {cleanup_error}"
                )
            raise

    def validate_report_config(self, config: Dict[str, Any]) -> bool:
        try:
            return self.report_generator.validate_configuration(config)
        except Exception as e:
            logger.error(f"Error validating report config: {e}")
            return False

    def get_supported_options(self) -> Dict[str, Any]:
        try:
            return self.report_generator.get_supported_providers()
        except Exception as e:
            logger.error(f"Error getting supported options: {e}")
            return {}

    def cancel_generation(self, report_id: str) -> bool:
        try:
            return self.report_generator.cancel_generation(report_id)
        except Exception as e:
            logger.error(f"Error cancelling generation for report {report_id}: {e}")
            return False

__all__ = ["ReportGenerationService"]
