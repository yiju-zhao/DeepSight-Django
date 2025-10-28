"""
Celery tasks for notebooks app.

This package has been refactored into modules for better organization:
- _helpers.py: Shared helper functions
- ragflow_tasks.py: RAGFlow upload and status checking tasks
- processing_tasks.py: URL/file processing and parsing tasks (TODO)
- maintenance_tasks.py: Cleanup, health check, and testing tasks

All tasks are re-exported here for backward compatibility.
"""

# Import helper functions
from ._helpers import (
    _validate_task_inputs,
    _get_notebook_and_user,
    _get_or_create_knowledge_item,
    _update_batch_item_status,
    _check_batch_completion,
    _handle_task_completion,
    _handle_task_error,
)

# Import maintenance tasks
from .maintenance_tasks import (
    cleanup_old_batch_jobs,
    health_check_task,
    test_caption_generation_task,
)

# Import RAGFlow tasks
from .ragflow_tasks import (
    upload_to_ragflow_task,
    check_ragflow_status_task,
)

# Import processing tasks
from .processing_tasks import (
    parse_url_task,
    parse_url_with_media_task,
    parse_document_url_task,
    process_url_task,
    process_url_media_task,
    process_url_document_task,
    process_file_upload_task,
    generate_image_captions_task,
)

__all__ = [
    # Helper functions
    "_validate_task_inputs",
    "_get_notebook_and_user",
    "_get_or_create_knowledge_item",
    "_update_batch_item_status",
    "_check_batch_completion",
    "_handle_task_completion",
    "_handle_task_error",
    # RAGFlow tasks
    "upload_to_ragflow_task",
    "check_ragflow_status_task",
    # Processing tasks
    "parse_url_task",
    "parse_url_with_media_task",
    "parse_document_url_task",
    "process_url_task",
    "process_url_media_task",
    "process_url_document_task",
    "process_file_upload_task",
    "generate_image_captions_task",
    # Maintenance tasks
    "cleanup_old_batch_jobs",
    "test_caption_generation_task",
    "health_check_task",
]
