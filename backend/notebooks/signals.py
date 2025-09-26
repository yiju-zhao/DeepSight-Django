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


def _delete_ragflow_document_after_commit(dataset_id: str, document_id: str, document_title: str) -> None:
    """Schedule deletion of RagFlow document after the current transaction commits."""
    if not dataset_id or not document_id:
        return

    def _do_delete():
        try:
            from infrastructure.ragflow.client import get_ragflow_client
            ragflow_client = get_ragflow_client()

            success = ragflow_client.delete_document(dataset_id, document_id)
            if success:
                logger.info(f"Successfully deleted RagFlow document '{document_title}' (ID: {document_id}) from dataset {dataset_id}")
            else:
                logger.warning(f"RagFlow document deletion returned False for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete RagFlow document {document_id} ('{document_title}') from dataset {dataset_id}: {e}")

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
    """Delete all MinIO files and RagFlow documents related to a KnowledgeBaseItem when it is deleted.

    Includes:
      - processed content file (file_object_key)
      - original uploaded file (original_file_object_key)
      - any additional content files recorded in file_metadata (mineru_extraction)
      - image files are handled by KnowledgeBaseImage signal; we also sweep any
        image keys present in metadata as a safety net
      - RagFlow document deletion if ragflow_document_id exists
    """
    try:
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

        # Schedule MinIO file deletions
        _delete_object_keys_after_commit(keys)

        # Schedule RagFlow document deletion if exists
        if instance.ragflow_document_id and instance.notebook.ragflow_dataset_id:
            _delete_ragflow_document_after_commit(
                instance.notebook.ragflow_dataset_id,
                instance.ragflow_document_id,
                instance.title
            )

    except Exception as e:
        logger.error(f"Error scheduling KB item file deletions for {instance.id}: {e}")

