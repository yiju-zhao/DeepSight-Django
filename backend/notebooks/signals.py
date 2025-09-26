"""
Signals for notebooks app: ensure MinIO objects are deleted when DB rows are removed.

Best practice: collect object keys in pre_delete and perform deletions after
the database transaction commits (transaction.on_commit) to avoid deleting
files when a transaction is rolled back.
"""

import logging
from typing import List, Set

from django.db import transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import KnowledgeBaseItem, KnowledgeBaseImage
from infrastructure.storage.adapters import get_storage_backend


logger = logging.getLogger(__name__)


def _delete_object_keys_after_commit(keys: List[str]) -> None:
    """Schedule deletion of MinIO object keys after the current transaction commits."""
    # Deduplicate and filter falsy keys
    key_set: Set[str] = {k for k in keys if k}
    if not key_set:
        return

    def _do_delete():
        storage = get_storage_backend()
        deleted = 0
        for key in key_set:
            try:
                if storage.delete_file(key):
                    deleted += 1
                else:
                    logger.warning(f"Storage delete returned False for key: {key}")
            except Exception as e:
                logger.error(f"Failed to delete object key {key}: {e}")
        logger.info(f"Deleted {deleted}/{len(key_set)} MinIO objects for KB cleanup")

    # Ensure deletion runs only after a successful commit
    try:
        transaction.on_commit(_do_delete)
    except Exception:
        # If no transaction is in progress, run immediately
        _do_delete()



@receiver(pre_delete, sender=KnowledgeBaseImage)
def delete_image_file_on_pre_delete(sender, instance: KnowledgeBaseImage, using, **kwargs):
    """Delete the image file from MinIO when a KnowledgeBaseImage row is deleted."""
    try:
        keys: List[str] = []
        if instance.minio_object_key:
            keys.append(instance.minio_object_key)
        _delete_object_keys_after_commit(keys)
    except Exception as e:
        logger.error(f"Error scheduling image file deletion for {instance.id}: {e}")


@receiver(pre_delete, sender=KnowledgeBaseItem)
def delete_kb_files_on_pre_delete(sender, instance: KnowledgeBaseItem, using, **kwargs):
    """Delete RagFlow documents first, then MinIO files when a KnowledgeBaseItem is deleted.

    Order of operations:
    1. Delete RagFlow document immediately (while we still have the ID)
    2. Schedule MinIO file deletions for after commit

    Includes:
      - RagFlow document deletion if ragflow_document_id exists
      - processed content file (file_object_key)
      - original uploaded file (original_file_object_key)
      - any additional content files recorded in file_metadata (mineru_extraction)
      - image files are handled by KnowledgeBaseImage signal; we also sweep any
        image keys present in metadata as a safety net
    """
    try:
        # STEP 1: Delete RagFlow document IMMEDIATELY (before DB deletion)
        # We need to do this now because we need the IDs before they're lost
        if instance.ragflow_document_id and instance.notebook.ragflow_dataset_id:
            logger.info(f"Deleting RagFlow document '{instance.title}' (ID: {instance.ragflow_document_id}) from dataset {instance.notebook.ragflow_dataset_id}")
            try:
                from infrastructure.ragflow.client import get_ragflow_client
                ragflow_client = get_ragflow_client()

                success = ragflow_client.delete_document(
                    instance.notebook.ragflow_dataset_id,
                    instance.ragflow_document_id
                )
                if success:
                    logger.info(f"Successfully deleted RagFlow document '{instance.title}' (ID: {instance.ragflow_document_id}) from dataset {instance.notebook.ragflow_dataset_id}")

                    # Trigger dataset update to refresh embeddings after document deletion
                    try:
                        ragflow_client.update_dataset(instance.notebook.ragflow_dataset_id)
                        logger.info(f"Successfully updated RagFlow dataset {instance.notebook.ragflow_dataset_id} after document deletion")
                    except Exception as update_error:
                        # Log error but don't fail the deletion process
                        logger.warning(f"Failed to update dataset {instance.notebook.ragflow_dataset_id} after deletion: {update_error}")
                else:
                    logger.warning(f"RagFlow document deletion returned False for document {instance.ragflow_document_id}")
            except Exception as e:
                logger.error(f"Failed to delete RagFlow document {instance.ragflow_document_id} ('{instance.title}') from dataset {instance.notebook.ragflow_dataset_id}: {e}")

        # STEP 2: Collect MinIO object keys for later deletion
        keys: List[str] = []

        # Primary files
        if instance.file_object_key:
            keys.append(instance.file_object_key)
        if instance.original_file_object_key:
            keys.append(instance.original_file_object_key)

        # Sweep metadata for any stored object keys
        fm = instance.file_metadata if isinstance(instance.file_metadata, dict) else {}
        if fm:
            # Known list of image keys
            image_keys = fm.get('image_object_keys') or []
            if isinstance(image_keys, list):
                keys.extend([str(k) for k in image_keys if k])

            # MinerU extraction may store content_files and image_files with object_key
            mineru = fm.get('mineru_extraction') or {}
            if isinstance(mineru, dict):
                for group in ('content_files', 'image_files'):
                    files = mineru.get(group) or []
                    if isinstance(files, list):
                        for ent in files:
                            try:
                                obj_key = ent.get('object_key')
                                if obj_key:
                                    keys.append(str(obj_key))
                            except Exception:
                                continue

        # STEP 3: Schedule MinIO file deletions for after commit
        _delete_object_keys_after_commit(keys)

    except Exception as e:
        logger.error(f"Error during KB item deletion for {instance.id}: {e}")

