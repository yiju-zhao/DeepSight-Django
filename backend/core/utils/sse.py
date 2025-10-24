"""
Server-Sent Events (SSE) utilities for real-time job status updates.

Uses Redis Pub/Sub for event broadcasting from Celery tasks to SSE endpoints.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


def publish_notebook_event(
    notebook_id: str,
    entity: str,
    entity_id: str,
    status: str,
    payload: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Publish a job status event to Redis for SSE streaming.

    Events are published to: sse:notebook:{notebook_id}

    Args:
        notebook_id: The notebook UUID
        entity: Entity type ('podcast' or 'report')
        entity_id: The entity UUID/ID
        status: Job status ('STARTED', 'SUCCESS', 'FAILURE', 'CANCELLED')
        payload: Optional additional data (e.g., audio_object_key, pdf_key)

    Returns:
        True if published successfully, False otherwise

    Example:
        publish_notebook_event(
            notebook_id="abc-123",
            entity="podcast",
            entity_id="def-456",
            status="SUCCESS",
            payload={"audio_object_key": "path/to/audio.wav"}
        )
    """
    if not notebook_id:
        logger.warning("publish_notebook_event called with empty notebook_id, skipping")
        return False

    try:
        # Build the message
        message = {
            "entity": entity,
            "id": str(entity_id),
            "notebookId": str(notebook_id),
            "status": status,
            "ts": datetime.utcnow().isoformat() + "Z",
        }

        if payload:
            message["payload"] = payload

        # Get Redis client and publish
        redis_client = redis.Redis.from_url(
            settings.CELERY_BROKER_URL,
            decode_responses=True
        )

        channel = f"sse:notebook:{notebook_id}"
        redis_client.publish(channel, json.dumps(message))

        logger.info(
            f"Published {entity} event to {channel}: "
            f"id={entity_id}, status={status}"
        )
        return True

    except Exception as e:
        # Log error but don't raise - publishing failures shouldn't break the main task
        logger.error(
            f"Failed to publish notebook event: "
            f"notebook_id={notebook_id}, entity={entity}, "
            f"entity_id={entity_id}, status={status}, error={e}",
            exc_info=True
        )
        return False


def build_job_event(
    entity: str,
    entity_id: str,
    notebook_id: str,
    status: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a standardized job event message.

    This is a helper function for constructing event messages before publishing.

    Args:
        entity: Entity type ('podcast' or 'report')
        entity_id: The entity UUID/ID
        notebook_id: The notebook UUID
        status: Job status ('STARTED', 'SUCCESS', 'FAILURE', 'CANCELLED')
        payload: Optional additional data

    Returns:
        Event message dictionary
    """
    message = {
        "entity": entity,
        "id": str(entity_id),
        "notebookId": str(notebook_id),
        "status": status,
        "ts": datetime.utcnow().isoformat() + "Z",
    }

    if payload:
        message["payload"] = payload

    return message
