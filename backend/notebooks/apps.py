from django.apps import AppConfig


class NotebooksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notebooks"

    def ready(self):
        """Connect signal handlers for the notebooks app.

        Ensures pre_delete handlers (e.g., RagFlow document cleanup and MinIO
        file deletions) are registered when the app is loaded.
        """
        # Import within method to avoid side effects at import time
        try:
            from . import signals  # noqa: F401  (import for side effects)
        except Exception as e:
            # Log import issues rather than crashing app startup
            import logging
            logging.getLogger(__name__).exception(
                f"Failed to load notebooks signal handlers: {e}"
            )
