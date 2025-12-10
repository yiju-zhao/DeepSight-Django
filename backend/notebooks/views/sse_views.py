"""
Server-Sent Events views for real-time status updates
"""

import json
import logging
import time
from collections.abc import Generator
from typing import Any

import redis
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import KnowledgeBaseItem, Notebook

logger = logging.getLogger(__name__)

class FileStatusSSEView(View):
    @method_decorator(csrf_exempt)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def options(self, request, notebook_id: str, file_id: str):
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Accept, Authorization, Content-Type"
        return response

    def get(self, request, notebook_id: str, file_id: str):
        try:
            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_id
            )

            # Handle both upload IDs and UUID file IDs
            import re

            is_uuid = re.match(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
                file_id,
                re.IGNORECASE,
            )

            if is_uuid:
                # It's a UUID, look up by primary key
                file_item = get_object_or_404(
                    KnowledgeBaseItem.objects.filter(notebook=notebook), pk=file_id
                )
            else:
                # It's an upload ID, look up by title or create a placeholder response
                try:
                    file_item = KnowledgeBaseItem.objects.filter(
                        notebook=notebook, title__icontains=file_id
                    ).first()
                    if not file_item:
                        # Return a "not found yet" SSE stream for upload IDs that haven't been processed
                        return self._generate_upload_pending_stream(file_id)
                except Exception:
                    return self._generate_upload_pending_stream(file_id)

            response = StreamingHttpResponse(
                self.generate_file_status_stream(file_item),
                content_type="text/event-stream",
            )
            response["Cache-Control"] = "no-cache"
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Headers"] = (
                "Accept, Authorization, Content-Type"
            )
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            return response

        except Exception as e:
            logger.exception(f"Failed to create file status SSE stream: {e}")
            return HttpResponse(
                f"Error: {str(e)}", status=500, content_type="text/plain"
            )

    def generate_file_status_stream(
        self, file_item: KnowledgeBaseItem
    ) -> Generator[str, None, None]:
        try:
            max_iterations = 60
            iteration = 0
            logger.info(f"Starting SSE stream for file {file_item.id}")
            while iteration < max_iterations:
                file_item.refresh_from_db()
                status_data = self.build_status_data(file_item)
                sse_message = {"type": "file_status", "data": status_data}
                yield f"data: {json.dumps(sse_message)}\n\n"

                parsing_done = file_item.parsing_status in ["done", "failed"]
                caption_done = status_data.get("caption_status") in [
                    "completed",
                    "failed",
                    None,
                ]
                ragflow_done = status_data.get("ragflow_processing_status") in [
                    "completed",
                    "failed",
                    None,
                ]

                # Only close when parsing is done AND (no caption processing OR caption is done) AND (no ragflow OR ragflow is done)
                if parsing_done and caption_done and ragflow_done:
                    logger.info(
                        f"File {file_item.id} all processing finished - parsing: {file_item.parsing_status}, "
                        f"caption: {status_data.get('caption_status')}, ragflow: {status_data.get('ragflow_processing_status')}"
                    )
                    close_message = {"type": "close"}
                    yield f"data: {json.dumps(close_message)}\n\n"
                    break
                iteration += 1
                time.sleep(5)
            if iteration >= max_iterations:
                logger.warning(
                    f"SSE stream for file {file_item.id} reached max iterations"
                )
                timeout_message = {
                    "type": "timeout",
                    "message": "Status monitoring timed out",
                }
                yield f"data: {json.dumps(timeout_message)}\n\n"
        except Exception as e:
            logger.exception(
                f"Error in SSE stream generation for file {file_item.id}: {e}"
            )
            error_message = {"type": "error", "message": f"Stream error: {str(e)}"}
            yield f"data: {json.dumps(error_message)}\n\n"

    def build_status_data(self, file_item: KnowledgeBaseItem) -> dict[str, Any]:
        # Use the raw parsing_status for frontend consistency
        # Frontend expects: "queueing", "parsing", "captioning", "done", "failed"
        raw_status = file_item.parsing_status or "queueing"

        return {
            "file_id": str(file_item.id),
            "status": raw_status,  # Send raw status for frontend consistency
            "title": file_item.title,
            "content_type": file_item.content_type,
            "created_at": file_item.created_at.isoformat()
            if file_item.created_at
            else None,
            "updated_at": file_item.updated_at.isoformat()
            if file_item.updated_at
            else None,
            "has_content": bool(file_item.content),
            "processing_status": raw_status,  # Also include in processing_status for compatibility
            "metadata": file_item.metadata or {},
            "captioning_status": file_item.captioning_status,  # Use actual captioning_status field
            "ragflow_processing_status": file_item.ragflow_processing_status,  # Include RagFlow status
        }

    def _generate_upload_pending_stream(self, upload_id: str):
        """Generate SSE stream for upload IDs that haven't been processed yet"""

        def generate_pending_stream():
            # Send a few "processing" messages then close
            for _i in range(3):
                yield f"data: {json.dumps({'type': 'file_status', 'data': {'file_id': upload_id, 'status': 'processing', 'title': f'Upload {upload_id}', 'updated_at': None}})}\n\n"
                time.sleep(1)
            # Send close message
            yield f"data: {json.dumps({'type': 'close', 'message': 'Upload not found'})}\n\n"

        response = StreamingHttpResponse(
            generate_pending_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Accept, Authorization, Content-Type"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response


class NotebookJobsSSEView(View):
    """
    SSE endpoint for real-time job status updates (podcasts and reports).

    Subscribes to Redis Pub/Sub channel: sse:notebook:{notebook_id}
    Streams job events (STARTED, SUCCESS, FAILURE, CANCELLED) to the client.
    """

    MAX_DURATION_SECONDS = 600  # 10 minutes max connection time
    HEARTBEAT_INTERVAL = 30  # Send heartbeat every 30 seconds

    @method_decorator(csrf_exempt)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def options(self, request, notebook_id: str):
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Accept, Authorization, Content-Type"
        return response

    def get(self, request, notebook_id: str):
        """Stream job events for a specific notebook."""
        try:
            # Verify notebook ownership
            get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_id
            )

            logger.info(
                f"Starting job stream for notebook {notebook_id}, user {request.user.id}"
            )

            response = StreamingHttpResponse(
                self.generate_job_stream(notebook_id), content_type="text/event-stream"
            )
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"  # Disable nginx buffering
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Headers"] = (
                "Accept, Authorization, Content-Type"
            )
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            return response

        except Exception as e:
            logger.exception(f"Failed to create job SSE stream: {e}")
            return HttpResponse(
                f"Error: {str(e)}", status=500, content_type="text/plain"
            )

    def generate_job_stream(self, notebook_id: str) -> Generator[str, None, None]:
        """
        Generate SSE stream by subscribing to Redis Pub/Sub channel.

        Yields:
            SSE formatted messages with job status updates
        """
        redis_client = None
        pubsub = None

        try:
            # Connect to Redis
            redis_client = redis.Redis.from_url(
                settings.CELERY_BROKER_URL, decode_responses=True
            )
            pubsub = redis_client.pubsub()

            # Subscribe to notebook channel
            channel = f"sse:notebook:{notebook_id}"
            pubsub.subscribe(channel)

            logger.info(f"Subscribed to Redis channel: {channel}")

            # Send initial connection message (ensure UUID is JSON-serializable)
            yield f"data: {json.dumps({'type': 'connected', 'notebookId': str(notebook_id)})}\n\n"

            start_time = time.time()
            last_heartbeat = start_time
            last_event_data = None

            # Listen for messages with timeout
            while True:
                # Check max duration
                elapsed = time.time() - start_time
                if elapsed > self.MAX_DURATION_SECONDS:
                    logger.info(
                        f"Job stream for notebook {notebook_id} reached max duration"
                    )
                    yield f"data: {json.dumps({'type': 'timeout', 'message': 'Stream timeout'})}\n\n"
                    break

                # Get message with timeout
                message = pubsub.get_message(timeout=1.0)

                if message and message["type"] == "message":
                    # Forward the event to client, but avoid duplicate sends of identical payloads
                    event_data = message["data"]
                    if event_data != last_event_data:
                        yield f"data: {event_data}\n\n"
                        last_event_data = event_data
                        logger.debug(f"Forwarded event: {event_data}")
                    last_heartbeat = time.time()

                # Send heartbeat if idle
                elif time.time() - last_heartbeat > self.HEARTBEAT_INTERVAL:
                    yield ": heartbeat\n\n"
                    last_heartbeat = time.time()

        except GeneratorExit:
            logger.info(
                f"Client disconnected from job stream for notebook {notebook_id}"
            )

        except Exception as e:
            logger.exception(f"Error in job stream for notebook {notebook_id}: {e}")
            try:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            except:
                pass

        finally:
            # Clean up Redis connection
            if pubsub:
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except:
                    pass

            if redis_client:
                try:
                    redis_client.close()
                except:
                    pass

            logger.info(f"Closed job stream for notebook {notebook_id}")
