"""
New services package providing simplified, cohesive service modules
for the reports app. Initially, these wrap existing implementations
to allow a safe cutover; subsequent iterations can inline logic.
"""

from .generation import ReportGenerationService
from .image import ImageService
from .job import JobService
from .pdf import PdfService
from .deletion import ReportDeletionService, DeletionServiceFactory

__all__ = [
    "ReportGenerationService",
    "ImageService",
    "JobService",
    "PdfService",
    "ReportDeletionService",
    "DeletionServiceFactory",
]

