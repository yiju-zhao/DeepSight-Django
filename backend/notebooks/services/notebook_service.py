"""
Enhanced Notebook Service following Django best practices.

Handles notebook business logic with proper validation, permissions,
and transaction management.
"""

import logging

from core.services import ModelService
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models, transaction


class NotebookService(ModelService):
    """
    Service for notebook operations following Django patterns.

    Provides comprehensive notebook management with proper user
    permission checking, validation, and transaction management.
    """

    def __init__(self):
        from ..models import Notebook

        super().__init__(Notebook)
        self.logger = logging.getLogger(__name__)

    def perform_action(self, **kwargs):
        """
        Implementation of abstract method from BaseService.
        This service uses direct method calls rather than the template pattern.
        """
        # This method is required by BaseService but not used in this service
        # Individual methods handle their own transactions and validation
        pass

    def get_user_notebooks(
        self,
        user,
        with_stats: bool = False,
        filters: dict = None,
        page: int = 1,
        page_size: int = 20,
    ):
        """
        Get notebooks for a user with optional filtering and pagination.

        Args:
            user: User to get notebooks for
            with_stats: Whether to include statistics (source/item counts)
            filters: Optional filters to apply
            page: Page number for pagination
            page_size: Number of items per page

        Returns:
            Dict with notebooks, pagination info, and metadata
        """
        # Start with user's notebooks
        queryset = self.model_class.objects.for_user(user)

        # Apply statistics if requested
        if with_stats:
            queryset = queryset.with_stats()

        # Apply filters
        if filters:
            if "search" in filters and filters["search"]:
                search_term = filters["search"]
                queryset = queryset.filter(
                    models.Q(name__icontains=search_term)
                    | models.Q(description__icontains=search_term)
                )

            if "has_content" in filters and filters["has_content"]:
                queryset = queryset.active()

            if "recent_activity" in filters:
                days = filters.get("recent_activity_days", 30)
                queryset = queryset.with_recent_activity(days)

        # Paginate results
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        self.log_operation(
            "notebooks_retrieved",
            user_id=user.id,
            total_count=paginator.count,
            page=page,
            filters=filters or {},
        )

        return {
            "notebooks": list(page_obj),
            "pagination": {
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
            "stats": {
                "total_notebooks": paginator.count,
                "active_notebooks": queryset.active().count() if not filters else None,
            },
        }

    @transaction.atomic
    def create_notebook(self, user, name: str, description: str = ""):
        """
        Create a new notebook with validation.

        Args:
            user: User who will own the notebook
            name: Name of the notebook
            description: Optional description

        Returns:
            Created Notebook instance

        Raises:
            ValidationError: If validation fails
        """
        # Validate input
        if not name or not name.strip():
            raise ValidationError("Notebook name cannot be empty")

        # Check for duplicate names (case-insensitive)
        if self.model_class.objects.filter(
            user=user, name__iexact=name.strip()
        ).exists():
            raise ValidationError("A notebook with this name already exists")

        # Create notebook
        notebook = self.model_class(
            user=user,
            name=name.strip(),
            description=description.strip() if description else "",
        )
        notebook.full_clean()
        notebook.save()

        # Create RagFlow dataset for the notebook
        try:
            from infrastructure.ragflow.service import get_ragflow_service

            ragflow_service = get_ragflow_service()

            # Create dataset
            dataset = ragflow_service.create_dataset(
                name=f"notebook_{notebook.id}_{notebook.name}",
                description=notebook.description
                or f"Dataset for notebook '{notebook.name}'",
                chunk_token_num=2048,
            )

            # Update notebook with RagFlow dataset ID
            notebook.ragflow_dataset_id = dataset.id
            notebook.save()

            self.log_operation(
                "notebook_created_with_ragflow_dataset",
                notebook_id=str(notebook.id),
                user_id=user.id,
                name=notebook.name,
                ragflow_dataset_id=dataset.id,
            )

        except ValidationError:
            # Re-raise ValidationError to maintain the interface
            raise
        except Exception as e:
            # For any other error, rollback and raise ValidationError
            notebook.delete()
            self.logger.error(
                f"Failed to create RagFlow dataset for notebook {name}: {e}"
            )
            raise ValidationError(f"Failed to create notebook: {str(e)}") from e

        return notebook

    @transaction.atomic
    def update_notebook(self, notebook_id: str, user, **updates):
        """
        Update a notebook with validation and permission checking.

        Args:
            notebook_id: ID of the notebook to update
            user: User who owns the notebook
            **updates: Fields to update

        Returns:
            Updated Notebook instance

        Raises:
            PermissionDenied: If user doesn't own the notebook
            ValidationError: If validation fails
        """
        # Get notebook with permission check
        notebook = self.get_object_for_user(notebook_id, user)

        # Apply updates
        updated_fields = []
        for field, value in updates.items():
            if hasattr(notebook, field) and field in ["name", "description"]:
                if field == "name":
                    value = value.strip() if value else ""
                    if not value:
                        raise ValidationError("Notebook name cannot be empty")

                    # Check for duplicate names (excluding current notebook)
                    if (
                        self.model_class.objects.filter(user=user, name__iexact=value)
                        .exclude(pk=notebook.pk)
                        .exists()
                    ):
                        raise ValidationError(
                            "A notebook with this name already exists"
                        )

                elif field == "description":
                    value = value.strip() if value else ""

                setattr(notebook, field, value)
                updated_fields.append(field)

        # Validate and save
        if updated_fields:
            notebook.full_clean()
            updated_fields.append("updated_at")
            notebook.save(update_fields=updated_fields)

            self.log_operation(
                "notebook_updated",
                notebook_id=notebook_id,
                user_id=user.id,
                updated_fields=updated_fields,
            )

        return notebook

    @transaction.atomic
    def delete_notebook(self, notebook_id: str, user):
        """
        Delete a notebook with permission checking.

        Args:
            notebook_id: ID of the notebook to delete
            user: User who owns the notebook

        Returns:
            Dict with deletion statistics

        Raises:
            PermissionDenied: If user doesn't own the notebook
        """
        # Get notebook with permission check
        notebook = self.get_object_for_user(notebook_id, user)

        # Collect statistics before deletion
        stats = {
            "notebook_name": notebook.name,
            "knowledge_items_count": notebook.knowledge_base_items.count(),
            "chat_sessions_count": notebook.chat_sessions.count(),
            "batch_jobs_count": notebook.batch_jobs.count(),
        }

        # Clean up external resources before deleting notebook
        self._cleanup_external_resources(notebook)

        # Delete notebook (cascade will handle related objects)
        notebook.delete()

        self.log_operation(
            "notebook_deleted", notebook_id=notebook_id, user_id=user.id, **stats
        )

        return stats

    def get_notebook_stats(self, notebook_id: str, user):
        """
        Get comprehensive statistics for a notebook.

        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook

        Returns:
            Dict with notebook statistics
        """
        from datetime import timedelta

        from django.utils import timezone

        # Get notebook with permission check
        notebook = self.get_object_for_user(notebook_id, user)

        # Get processing status summary
        processing_status = notebook.get_processing_status_summary()

        # Get content type summary
        content_types = notebook.get_content_types_summary()

        # Get recent activity
        last_week = timezone.now() - timedelta(days=7)
        recent_items = notebook.knowledge_base_items.filter(
            created_at__gte=last_week
        ).count()

        # Count recent messages across all sessions
        from ..models import SessionChatMessage

        recent_messages = SessionChatMessage.objects.filter(
            notebook=notebook, timestamp__gte=last_week
        ).count()

        total_messages = SessionChatMessage.objects.filter(notebook=notebook).count()

        stats = {
            "basic_info": {
                "name": notebook.name,
                "description": notebook.description,
                "created_at": notebook.created_at,
                "updated_at": notebook.updated_at,
            },
            "content_counts": {
                "knowledge_items": notebook.knowledge_base_items.count(),
                "chat_sessions": notebook.chat_sessions.count(),
                "chat_messages": total_messages,
                "batch_jobs": notebook.batch_jobs.count(),
                "images": notebook.knowledge_base_items.with_images().count(),
            },
            "parsing_status": processing_status,
            "content_types": content_types,
            "recent_activity": {
                "items_last_week": recent_items,
                "messages_last_week": recent_messages,
            },
            "storage_info": {
                "has_processed_content": notebook.has_processed_content(),
                "items_with_files": notebook.knowledge_base_items.with_files().count(),
            },
        }

        self.log_operation(
            "notebook_stats_retrieved", notebook_id=notebook_id, user_id=user.id
        )

        return stats

    @transaction.atomic
    def duplicate_notebook(self, notebook_id: str, user, new_name: str):
        """
        Create a duplicate of an existing notebook.

        Args:
            notebook_id: ID of the notebook to duplicate
            user: User who owns the notebook
            new_name: Name for the new notebook

        Returns:
            New Notebook instance
        """
        # Get original notebook
        original = self.get_object_for_user(notebook_id, user)

        # Create duplicate notebook
        duplicate = self.create_notebook(
            user=user, name=new_name, description=f"Copy of {original.name}"
        )

        # Note: Knowledge items are not duplicated as they may reference
        # external storage. This would require a separate service method
        # to handle content duplication properly.

        self.log_operation(
            "notebook_duplicated",
            original_notebook_id=notebook_id,
            new_notebook_id=str(duplicate.id),
            user_id=user.id,
        )

        return duplicate

    def cleanup_empty_notebooks(self, user, older_than_days: int = 30):
        """
        Clean up empty notebooks older than specified days.

        Args:
            user: User whose notebooks to clean up
            older_than_days: Delete notebooks older than this many days

        Returns:
            Number of notebooks deleted
        """
        from datetime import timedelta

        from django.utils import timezone

        cutoff_date = timezone.now() - timedelta(days=older_than_days)

        # Find empty notebooks older than cutoff
        empty_notebooks = self.model_class.objects.filter(
            user=user, created_at__lt=cutoff_date, knowledge_base_items__isnull=True
        ).distinct()

        count = empty_notebooks.count()
        if count > 0:
            notebook_names = list(empty_notebooks.values_list("name", flat=True))
            empty_notebooks.delete()

            self.log_operation(
                "empty_notebooks_cleaned",
                user_id=user.id,
                count=count,
                notebook_names=notebook_names,
            )

        return count

    # RagFlow Integration Methods

    def has_ragflow_integration(self, notebook_id: str, user) -> bool:
        """
        Check if notebook has RagFlow integration configured.

        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook

        Returns:
            True if RagFlow IDs are configured
        """
        try:
            notebook = self.get_object_for_user(notebook_id, user)
            return bool(
                notebook.ragflow_dataset_id
                or notebook.ragflow_agent_id
                or notebook.ragflow_chat_id
            )
        except Exception:
            return False

    def get_ragflow_status(self, notebook_id: str, user):
        """
        Get RagFlow integration status for a notebook.

        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook

        Returns:
            Dict with RagFlow integration information
        """
        try:
            notebook = self.get_object_for_user(notebook_id, user)

            return {
                "has_integration": self.has_ragflow_integration(notebook_id, user),
                "dataset_id": notebook.ragflow_dataset_id,
                "agent_id": notebook.ragflow_agent_id,
                "chat_id": notebook.ragflow_chat_id,
                "created_at": notebook.created_at,
                "updated_at": notebook.updated_at,
            }

        except Exception as e:
            self.logger.exception(
                f"Failed to get RagFlow status for notebook {notebook_id}: {e}"
            )
            return {"has_integration": False, "error": str(e)}

    def _cleanup_external_resources(self, notebook):
        """
        Clean up external RagFlow resources associated with a notebook.

        Args:
            notebook: Notebook instance to clean up
        """
        try:
            from infrastructure.ragflow.service import get_ragflow_service

            ragflow_service = get_ragflow_service()

            # Delete chat assistant and its sessions
            # Note: ragflow_agent_id actually stores chat_id (naming kept for backward compat)
            chat_ids_to_delete = []
            if notebook.ragflow_agent_id:
                chat_ids_to_delete.append(notebook.ragflow_agent_id)
            if (
                notebook.ragflow_chat_id
                and notebook.ragflow_chat_id != notebook.ragflow_agent_id
            ):
                chat_ids_to_delete.append(notebook.ragflow_chat_id)

            for chat_id in chat_ids_to_delete:
                try:
                    # Delete all sessions for this chat assistant
                    ragflow_service.delete_chat_sessions(
                        chat_id=chat_id, session_ids=None
                    )
                    self.logger.info(
                        f"Deleted all sessions for chat assistant: {chat_id}"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to delete chat sessions for {chat_id}: {e}"
                    )

                try:
                    # Delete the chat assistant
                    ragflow_service.delete_chat(chat_id)
                    self.logger.info(f"Deleted chat assistant: {chat_id}")
                except Exception as e:
                    self.logger.warning(
                        f"Failed to delete chat assistant {chat_id}: {e}"
                    )

            # Delete dataset (includes all documents)
            if notebook.ragflow_dataset_id:
                try:
                    ragflow_service.delete_dataset(notebook.ragflow_dataset_id)
                    self.logger.info(
                        f"Deleted RagFlow dataset: {notebook.ragflow_dataset_id}"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to delete RagFlow dataset {notebook.ragflow_dataset_id}: {e}"
                    )

        except Exception as e:
            self.logger.error(
                f"Error during RagFlow cleanup for notebook {notebook.id}: {e}"
            )
