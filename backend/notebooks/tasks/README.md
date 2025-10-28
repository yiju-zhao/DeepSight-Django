# Notebooks Tasks Refactoring

## Overview

The `notebooks/tasks.py` file (1364 lines) has been refactored into a modular structure for better maintainability and organization.

## New Structure

```
notebooks/tasks/
├── __init__.py              # Re-exports all tasks for backward compatibility
├── _helpers.py              # Shared helper functions (COMPLETE)
├── maintenance_tasks.py     # Cleanup and health check tasks (COMPLETE)
├── ragflow_tasks.py         # RAGFlow integration tasks (TODO)
└── processing_tasks.py      # URL/file processing tasks (TODO)
```

## Migration Status

### ✅ Completed
- `_helpers.py` - All shared helper functions extracted
- `maintenance_tasks.py` - All maintenance tasks migrated:
  - `cleanup_old_batch_jobs`
  - `test_caption_generation_task`
  - `health_check_task`
- `__init__.py` - Backward compatibility layer created

### 🚧 To Do
- `ragflow_tasks.py` - Move RAGFlow-related tasks:
  - `upload_to_ragflow_task` (line 98 in original)
  - `check_ragflow_status_task` (line 1228 in original)

- `processing_tasks.py` - Move processing tasks:
  - `parse_url_task` (line 360)
  - `parse_url_with_media_task` (line 458)
  - `parse_document_url_task` (line 562)
  - `process_url_task` (line 771)
  - `process_url_media_task` (line 863)
  - `process_url_document_task` (line 945)
  - `process_file_upload_task` (line 1027)
  - `generate_image_captions_task` (line 1136)

## Backward Compatibility

The `__init__.py` file ensures that all existing imports continue to work:

```python
# Old import (still works)
from notebooks.tasks import cleanup_old_batch_jobs

# New import (also works)
from notebooks.tasks.maintenance_tasks import cleanup_old_batch_jobs
```

## Benefits

1. **Better Organization**: Tasks are grouped by functionality
2. **Easier Testing**: Smaller, focused modules are easier to test
3. **Improved Maintainability**: Changes to one category don't affect others
4. **Clearer Dependencies**: Each module imports only what it needs
5. **Backward Compatible**: No breaking changes to existing code

## Next Steps

1. Create `ragflow_tasks.py` with the two RAGFlow tasks
2. Create `processing_tasks.py` with the eight processing tasks
3. Update `__init__.py` to import from the new modules
4. Remove or deprecate the original `tasks.py`
5. Update Celery routing configuration if needed

## Testing

After completing the refactoring:

1. Run Celery worker: `celery -A backend worker -l info`
2. Verify all tasks are registered: `celery -A backend inspect registered`
3. Test each task type:
   - Upload a file (processing tasks)
   - Check RAGFlow status (RAGFlow tasks)
   - Run cleanup (maintenance tasks)

## Notes

- All task names and signatures remain unchanged
- Celery routing configuration in `backend/celery.py` doesn't need changes
- The `@shared_task` decorator ensures tasks are properly registered
- Helper functions are prefixed with `_` to indicate they're internal
