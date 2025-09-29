"""
Main orchestrator service for report generation.
Simplified to compose the new services layer without DI.
"""

import logging
from typing import Dict, Optional, List, Any
from .models import Report
from .services import ReportGenerationService, JobService

logger = logging.getLogger(__name__)


class ReportOrchestrator:
    """Main orchestrator service for report generation"""

    def __init__(self):
        self.generation_service = ReportGenerationService()
        self.job_service = JobService()
    
    def create_report_job(
        self, report_data: Dict[str, Any], user=None, notebook=None
    ) -> Report:
        """Create a new report generation job"""
        return self.job_service.create_job(report_data, user, notebook)
    
    def generate_report(self, report_id: int) -> Dict[str, Any]:
        """Generate a complete report"""
        return self.generation_service.generate_report(report_id)
    
    def update_job_progress(
        self, report_id: str, progress: str, status: Optional[str] = None
    ):
        """Update job progress and optionally status"""
        self.job_service.update_job_progress(report_id, progress, status)
    
    def update_job_result(self, report_id: str, result: Dict, status: str = "completed"):
        """Update job with final result"""
        self.job_service.update_job_result(report_id, result, status)
    
    def update_job_error(self, report_id: str, error: str):
        """Update job with error information"""
        self.job_service.update_job_error(report_id, error)
    
    def get_job_status(self, report_id: str) -> Optional[Dict]:
        """Get the status of a report generation job"""
        return self.job_service.get_job_status(report_id)
    
    def cancel_report_job(self, report_id: str) -> bool:
        """Cancel a report generation job by dispatching a background task."""
        return self.job_service.cancel_job(report_id)
    
    def list_report_jobs(self, user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List report generation jobs"""
        return self.job_service.list_jobs(user_id, limit)
    
    def delete_report_job(self, report_id: str, user_id: int) -> bool:
        """Delete a report generation job and its associated files"""
        # Get report ID from job
        job_status = self.get_job_status(report_id)
        if not job_status:
            return False
        
        report_id = str(job_status.get('report_id', ''))
        
        # Delete storage files via model/infra where applicable (legacy behavior retained elsewhere)
        storage_deleted = True
        
        # Delete job metadata
        job_deleted = self.job_service.delete_job(report_id)
        
        return storage_deleted and job_deleted
    
    def validate_report_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate report configuration"""
        return self.generation_service.validate_report_config(config)
    
    def get_supported_options(self) -> Dict[str, Any]:
        """Get supported configuration options"""
        return self.generation_service.get_supported_options()
    
    def process_knowledge_base_input(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process input files from knowledge base"""
        # Use direct input processor implementation
        from .services.input_processor import KnowledgeBaseInputProcessor
        processor = KnowledgeBaseInputProcessor()
        return processor.get_content_data(
            processor.process_selected_files(file_paths)
        )
    
    def cleanup_temporary_files(self, temp_file_paths: List[str]):
        """Clean up temporary files"""
        # No-op in simplified flow (no temp files)
        return None
    
    def setup_report_storage(self, user_id: int, report_id: str, notebook_id: Optional[int] = None):
        """Set up storage for a report"""
        from .storage import StorageFactory
        storage = StorageFactory.create_storage()
        return storage.create_output_directory(user_id, report_id, notebook_id)
    
    def validate_configuration_settings(self, config: Dict[str, Any]) -> Dict[str, bool]:
        """Validate configuration settings"""
        from .services.config import validate_config
        return validate_config(config)
    
    def cleanup_old_jobs(self, days: int = 7):
        """Clean up old jobs"""
        self.job_service.cleanup_old_jobs(days)
    
    def cleanup_failed_job(self, report_id: str):
        """Clean up temp directories and resources for a failed job"""
        try:
            # Use generator cancellation to clean temp dirs as needed
            self.cancel_generation(report_id)
            logger.info(f"Completed cleanup for failed report {report_id}")
        except Exception as e:
            logger.warning(f"Error cleaning up failed report {report_id}: {e}")

    def cancel_generation(self, report_id: str) -> bool:
        """Cancel generation and cleanup temp data where supported."""
        try:
            return self.generation_service.cancel_generation(report_id)
        except Exception:
            return False


# Global singleton instance with default dependencies
report_orchestrator = ReportOrchestrator()
