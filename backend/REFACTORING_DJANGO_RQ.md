# Refactoring Plan: Migrating from Celery to Django-RQ

## 1. Objective

This document outlines the plan to migrate the background task processing system in the DeepSight Django backend from Celery to Django-RQ. The goal is to simplify the architecture, reduce complexity, and improve maintainability without sacrificing essential functionality.

## 2. Motivation

The current Celery implementation, while functional, is more complex than required for the project's needs. The primary benefits of switching to Django-RQ are:

*   **Simplicity:** Django-RQ is significantly easier to configure and manage than Celery. This will lower the barrier to entry for new developers and reduce the maintenance overhead.
*   **Reduced Dependencies:** The migration will allow us to remove the `celery` dependency and its related packages, resulting in a leaner `requirements.txt`.
*   **Built-in Dashboard:** Django-RQ provides a user-friendly web dashboard for monitoring queues, jobs, and workers out of the box, which is more convenient than setting up an external tool like Flower for Celery.
*   **Seamless Integration:** The project already uses Redis for caching and as the Celery broker, so no new infrastructure is required. Django-RQ uses Redis exclusively, making it a natural fit for our existing stack.

## 3. Prerequisites

Before starting the refactoring process, the following setup steps must be completed:

1.  **Install Dependencies:** Add `django-rq` and `rq-scheduler` to the `requirements.txt` file and install them:

    ```bash
    pip install django-rq rq-scheduler
    ```

2.  **Update `INSTALLED_APPS`:** Add `django_rq` to the `INSTALLED_APPS` in `backend/settings/base.py`:

    ```python
    # backend/settings/base.py

    THIRD_PARTY_APPS = [
        'rest_framework',
        'corsheaders',
        'drf_yasg',
        'storages',
        'django_rq',  # Add this line
    ]
    ```

3.  **Configure `RQ_QUEUES`:** Configure the queues in `backend/settings/base.py`. We will replicate the existing Celery queues.

    ```python
    # backend/settings/base.py

    RQ_QUEUES = {
        'default': {
            'HOST': os.getenv('REDIS_HOST', 'localhost'),
            'PORT': 6379,
            'DB': 0,
            'PASSWORD': os.getenv('REDIS_PASSWORD'),
            'DEFAULT_TIMEOUT': 3600,
        },
        'podcast': {
            'HOST': os.getenv('REDIS_HOST', 'localhost'),
            'PORT': 6379,
            'DB': 0,
            'PASSWORD': os.getenv('REDIS_PASSWORD'),
            'DEFAULT_TIMEOUT': 3600,
        },
        'maintenance': {
            'HOST': os.getenv('REDIS_HOST', 'localhost'),
            'PORT': 6379,
            'DB': 0,
            'PASSWORD': os.getenv('REDIS_PASSWORD'),
            'DEFAULT_TIMEOUT': 86400,
        },
        'reports': {
            'HOST': os.getenv('REDIS_HOST', 'localhost'),
            'PORT': 6379,
            'DB': 0,
            'PASSWORD': os.getenv('REDIS_PASSWORD'),
            'DEFAULT_TIMEOUT': 3600,
        },
        'validation': {
            'HOST': os.getenv('REDIS_HOST', 'localhost'),
            'PORT': 6379,
            'DB': 0,
            'PASSWORD': os.getenv('REDIS_PASSWORD'),
            'DEFAULT_TIMEOUT': 3600,
        },
        'notebook_processing': {
            'HOST': os.getenv('REDIS_HOST', 'localhost'),
            'PORT': 6379,
            'DB': 0,
            'PASSWORD': os.getenv('REDIS_PASSWORD'),
            'DEFAULT_TIMEOUT': 3600,
        },
    }
    ```

4.  **Add Django-RQ URLs:** Add the Django-RQ dashboard URLs to the project's `urls.py`.

    ```python
    # backend/urls.py

    from django.urls import path, include

    urlpatterns = [
        # ... other urls
        path('django-rq/', include('django_rq.urls')),
    ]
    ```

## 4. Step-by-Step Refactoring Plan

The refactoring will be done on an app-by-app basis to ensure a controlled and verifiable migration.

### Step 1: Refactor `notebooks/tasks.py`

This file contains the most tasks and is a good starting point.

1.  **Remove Celery Imports:** Remove `from celery import shared_task` and other Celery-related imports.
2.  **Refactor Task Definitions:** Convert `@shared_task` decorators to regular Python functions. The `bind=True` and `self` arguments are no longer needed.

    **Before:**
    ```python
    @shared_task(bind=True)
    def process_url_task(self, url: str, notebook_id: str, user_id: int, **kwargs):
        # ... task logic
    ```

    **After:**
    ```python
    def process_url_task(url: str, notebook_id: str, user_id: int, **kwargs):
        # ... task logic
    ```

3.  **Refactor Task Enqueueing:** Replace `.delay()` and `.apply_async()` calls with `django_rq.enqueue`.

    **Before:**
    ```python
    process_url_task.delay(url, notebook_id, user_id)
    ```

    **After:**
    ```python
    import django_rq
    queue = django_rq.get_queue('notebook_processing')
    queue.enqueue(process_url_task, url, notebook_id, user_id)
    ```

4.  **Handle Task Chaining:** For task chaining, enqueue the next task at the end of the current task.

    **Before:**
    ```python
    upload_to_ragflow_task.delay(str(kb_item.id))
    ```

    **After:**
    ```python
    import django_rq
    queue = django_rq.get_queue('notebook_processing')
    queue.enqueue(upload_to_ragflow_task, str(kb_item.id))
    ```

5.  **Handle Retries:** RQ supports automatic retries on failure.

    **Before (manual retry):**
    ```python
    raise self.retry(countdown=60, max_retries=max_retries)
    ```

    **After (automatic retry):**
    ```python
    # In the enqueue call
    queue.enqueue(check_ragflow_status_task, str(kb_item.id), retry=Retry(max=10, interval=60))
    ```
    This will require importing `from rq.retry import Retry`.

### Step 2: Refactor `podcast/tasks.py` and `reports/tasks.py`

Follow the same process as in Step 1 for the tasks in the `podcast` and `reports` apps, using their respective queues (`podcast` and `reports`).

### Step 3: Migrate Periodic Tasks (Celery Beat)

The Celery Beat schedules will be migrated to `rq-scheduler`.

1.  **Create Scheduler Configuration:** Create a new file, `scheduler.py`, in the `backend` directory.

    ```python
    # backend/scheduler.py

    import django_rq
    from rq_scheduler import Scheduler
    from datetime import timedelta

    # Import the tasks to be scheduled
    from podcast.tasks import cleanup_old_podcast_jobs
    from reports.tasks import cleanup_old_reports

    scheduler = Scheduler(queue_name='maintenance', connection=django_rq.get_connection('maintenance'))

    # Schedule daily tasks
    scheduler.schedule(
        scheduled_time=datetime.utcnow(),
        func=cleanup_old_podcast_jobs,
        interval=86400,  # Run daily
        repeat=None, # Repeat indefinitely
    )

    scheduler.schedule(
        scheduled_time=datetime.utcnow(),
        func=cleanup_old_reports,
        interval=86400,  # Run daily
        repeat=None, # Repeat indefinitely
    )
    ```

2.  **Run the Scheduler:** The `rqscheduler` command needs to be run as a separate process.

    ```bash
    python manage.py rqscheduler --queue maintenance
    ```

### Step 4: Update Worker Scripts

The scripts used to run the workers will need to be updated.

**Before:**
```bash
celery -A backend worker -l info -Q podcast
```

**After:**
```bash
python manage.py rqworker podcast
```

Update the `Procfile` or any other process management scripts accordingly.

## 5. Testing and Verification

After the refactoring is complete, the following steps should be taken to verify the migration:

1.  **Run Automated Tests:** Execute the project's test suite to ensure that no existing functionality has been broken.
2.  **Manual Task Verification:**
    *   Access the Django-RQ dashboard at `/django-rq/`.
    *   Manually trigger one of each type of task (e.g., process a URL, generate a report).
    *   Monitor the dashboard to ensure the jobs are enqueued, processed, and completed successfully.
3.  **Verify Periodic Tasks:** Check the `rq-scheduler` output and the dashboard to confirm that the cleanup tasks are being enqueued and executed at the correct intervals.
4.  **Error Handling:** Intentionally trigger a task that will fail and verify that the error is logged correctly in the dashboard and that the retry mechanism works as expected.

## 6. Rollback Plan

If critical issues are discovered during testing that cannot be resolved quickly, the following steps can be taken to roll back to the Celery implementation:

1.  **Revert Code:** Use Git to revert the codebase to the pre-migration state.
2.  **Uninstall Dependencies:** Uninstall `django-rq` and `rq-scheduler`.
3.  **Restart Workers:** Shut down the `rqworker` and `rqscheduler` processes and restart the Celery worker and Celery Beat processes.

## 7. Post-Migration Cleanup

Once the migration has been thoroughly tested and verified in a staging or production environment, the following cleanup tasks should be performed:

1.  **Remove Celery Dependencies:** Remove `celery` from `requirements.txt`.
2.  **Remove Celery Configuration:** Delete the Celery-related settings from `backend/settings/base.py`.
3.  **Delete `backend/celery.py`:** Delete the `backend/celery.py` file.
4.  **Update Documentation:** Update any internal documentation that refers to the Celery implementation.
