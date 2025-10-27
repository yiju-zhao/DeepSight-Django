import logging

from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from notebooks.models import Notebook
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Podcast
from .serializers import (
    PodcastCreateSerializer,
    PodcastListSerializer,
    PodcastSerializer,
)

logger = logging.getLogger(__name__)


# (Removed notebook-scoped views)


class PodcastJobListCreateView(APIView):
    """Canonical: List and create podcast jobs without notebook in path.

    - GET /api/v1/podcasts/jobs/?notebook=<uuid>
    - POST /api/v1/podcasts/jobs/ with body {..., notebook: <uuid>}
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            notebook_id = request.query_params.get("notebook")
            # Align with reports: do not surface cancelled items in list views
            qs = Podcast.objects.filter(user=request.user).exclude(status="cancelled")
            if notebook_id:
                notebook = get_object_or_404(
                    Notebook.objects.filter(user=request.user), pk=notebook_id
                )
                qs = qs.filter(notebook=notebook)

            jobs = qs.order_by("-created_at")
            serializer = PodcastListSerializer(jobs, many=True)

            response = Response(serializer.data)
            if jobs:
                last_modified = max(job.updated_at for job in jobs)
                response["Last-Modified"] = last_modified.strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                )

            has_active_jobs = any(
                job_data.get("status") in ["pending", "generating"]
                for job_data in serializer.data
            )
            cache_timeout = 2 if has_active_jobs else 5
            response["Cache-Control"] = f"max-age={cache_timeout}, must-revalidate"
            return response
        except Exception as e:
            logger.error(f"Error listing podcast jobs: {e}")
            return Response(
                {"error": f"Failed to list jobs: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request):
        try:
            serializer = PodcastCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user),
                pk=serializer.validated_data["notebook"],
            )

            source_file_ids = serializer.validated_data["source_file_ids"]
            title = serializer.validated_data.get("title", "Panel Conversation")
            description = serializer.validated_data.get("description", "")
            language = serializer.validated_data.get("language", "en")

            job = Podcast.objects.create(
                user=request.user,
                notebook=notebook,
                title=title,
                description=description,
                source_file_ids=source_file_ids,
                source_metadata={"language": language},
                status="pending",
            )

            from .tasks import process_podcast_generation

            task_result = process_podcast_generation.delay(str(job.id))
            job.celery_task_id = task_result.id
            job.save()

            response_serializer = PodcastSerializer(job)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating podcast job (canonical): {e}")
            return Response(
                {"error": f"Failed to create podcast-job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PodcastJobDetailView(generics.RetrieveDestroyAPIView):
    """
    Canonical: Retrieve or delete a specific podcast job by job_id.
    Handles GET and DELETE requests for a podcast job.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PodcastSerializer
    lookup_field = "id"
    lookup_url_kwarg = "job_id"

    def get_queryset(self):
        """Ensure users can only access their own podcasts."""
        return Podcast.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Replicate report deletion behavior:
        - Disallow deleting pending/generating; instruct to cancel first
        - Delete MinIO audio if present, then delete DB record
        - Return JSON payload with success + previous_status (HTTP 200)
        """
        try:
            instance = self.get_object()

            logger.info(
                f"DELETE request for podcast {instance.id} (status: {instance.status})"
            )

            # Disallow deletion of running/pending jobs
            if instance.status in ["pending", "generating"]:
                return Response(
                    {
                        "detail": f"Cannot delete job in '{instance.status}' status. Use POST /{instance.id}/cancel/ to cancel running jobs first.",
                        "current_status": instance.status,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Delete associated audio from storage (best-effort)
            if instance.audio_object_key:
                try:
                    from notebooks.utils.storage import get_minio_backend

                    minio_backend = get_minio_backend()
                    minio_backend.delete_file(instance.audio_object_key)
                    logger.info(
                        f"Successfully deleted podcast audio file for job {instance.id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error deleting podcast audio file for job {instance.id}: {e}"
                    )

            previous_status = instance.status
            instance_id = str(instance.id)
            instance.delete()

            resp = Response(
                {
                    "success": True,
                    "message": f"Job podcast {instance_id} successfully deleted",
                    "podcast_id": instance_id,
                    "previous_status": previous_status,
                },
                status=status.HTTP_200_OK,
            )
            # Add cache headers similar to report flow
            resp["Cache-Control"] = "no-cache, no-store, must-revalidate"
            resp["Pragma"] = "no-cache"
            resp["Expires"] = "0"
            return resp
        except Exception as e:
            job_id = kwargs.get(self.lookup_url_kwarg)
            logger.error(f"Error deleting podcast job {job_id}: {e}")
            return Response(
                {
                    "success": False,
                    "message": f"Failed to delete job podcast {job_id}",
                    "detail": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class PodcastJobCancelView(APIView):
    """Canonical: Cancel a podcast job by job_id (follows report cancel pattern)"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, job_id):
        """Cancel a running or pending podcast job immediately with SIGKILL"""
        try:
            job = get_object_or_404(
                Podcast.objects.filter(user=request.user), id=job_id
            )

            # Check if job is in a cancellable state
            if job.status not in ["pending", "generating"]:
                return Response(
                    {
                        "detail": f"Job cannot be cancelled. Current status: {job.status}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(
                f"Cancelling podcast {job_id} (status: {job.status}, celery_task_id: {job.celery_task_id})"
            )

            # Step 1: Immediately revoke Celery task with SIGKILL for non-ignorable termination
            if job.celery_task_id:
                try:
                    from backend.celery import app as celery_app

                    # Use SIGKILL for immediate, non-ignorable termination
                    celery_app.control.revoke(
                        job.celery_task_id, terminate=True, signal="SIGKILL"
                    )
                    logger.info(
                        f"Sent SIGKILL to Celery task {job.celery_task_id} for immediate termination"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to revoke Celery task {job.celery_task_id}: {e}"
                    )

            # Step 2: Update Podcast status to cancelled
            job.status = "cancelled"
            job.error_message = "Job cancelled by user"
            job.save(update_fields=["status", "error_message", "updated_at"])

            # Step 3: No Redis/SSE updates required

            # Log cancellation with details
            logger.info(
                f"✓ Podcast generation cancelled successfully:\n"
                f"  - Podcast ID: {job_id}\n"
                f"  - Celery Task ID: {job.celery_task_id}\n"
                f"  - Status: cancelled\n"
                f"  - User: {request.user.username}"
            )

            return Response(
                {
                    "job_id": str(job_id),
                    "status": "cancelled",
                    "message": "Job has been cancelled successfully",
                },
                status=status.HTTP_200_OK,
            )

        except Podcast.DoesNotExist:
            return Response(
                {"detail": "Podcast not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error cancelling job podcast {job_id}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error cancelling job: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def podcast_job_status_stream(request, podcast_id):
    # SSE removed. Kept stub for backwards-compatibility to avoid 404 if wired elsewhere.
    return HttpResponse(status=410)


# ==============================
# Report-style views (no 'jobs')
# ==============================


class PodcastListCreateView(PodcastJobListCreateView):
    pass


class PodcastDetailView(PodcastJobDetailView):
    lookup_url_kwarg = "podcast_id"


class PodcastCancelView(PodcastJobCancelView):
    def post(self, request, podcast_id):
        return super().post(request, job_id=podcast_id)


# Legacy streaming audio routes removed in favor of redirect gateway


class PodcastAudioRedirectView(APIView):
    """Stream podcast audio file through Django (avoids CORS and presigned URL issues).

    - GET /api/v1/podcasts/{podcast_id}/audio/
      Streams audio file from MinIO through Django.
      Optional query param: download=1 to trigger download instead of inline playback.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, podcast_id):
        try:
            job = get_object_or_404(
                Podcast.objects.filter(user=request.user), id=podcast_id
            )
            if not job.audio_object_key:
                return Response(
                    {"error": "Audio file not available"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Stream file from MinIO through Django
            from notebooks.utils.storage import get_minio_backend

            minio_backend = get_minio_backend()

            file_iter, content_length, content_type = minio_backend.stream_file(
                job.audio_object_key
            )

            if not file_iter:
                return Response(
                    {"error": "Audio file not accessible"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Determine content disposition based on download parameter
            if request.GET.get("download"):
                safe_title = "".join(
                    c
                    for c in (job.title or "podcast")
                    if c.isalnum() or c in (" ", "-", "_")
                ).rstrip()
                filename = (
                    f"{safe_title}.wav" if safe_title else f"podcast-{job.id}.wav"
                )
                disposition = f'attachment; filename="{filename}"'
            else:
                disposition = "inline"

            # Create streaming response
            response = StreamingHttpResponse(
                file_iter, content_type=content_type or "audio/wav"
            )
            response["Content-Disposition"] = disposition

            if content_length:
                response["Content-Length"] = content_length

            # Add CORS headers for audio playback
            response["Access-Control-Allow-Origin"] = request.META.get(
                "HTTP_ORIGIN", "*"
            )
            response["Access-Control-Allow-Credentials"] = "true"
            response["Accept-Ranges"] = "bytes"

            return response

        except Exception as e:
            logger.error(f"Error streaming audio for podcast {podcast_id}: {e}")
            return Response(
                {"error": f"Failed to stream audio: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PodcastFilesView(APIView):
    """Return stable gateway URLs for podcast files (two-step pattern).

    - GET /api/v1/podcasts/{podcast_id}/files/
      Returns JSON listing available files with stable download_url.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, podcast_id):
        try:
            job = get_object_or_404(
                Podcast.objects.filter(user=request.user), id=podcast_id
            )
            files = []

            if getattr(job, "audio_object_key", None):
                # Prefer filename from stored metadata; otherwise derive from title/id
                filename = None
                try:
                    metadata = getattr(job, "file_metadata", None) or {}
                    if isinstance(metadata, dict):
                        filename = metadata.get("filename") or metadata.get(
                            "main_report_filename"
                        )
                except Exception:
                    filename = None

                if not filename:
                    safe_title = "".join(
                        c
                        for c in (job.title or "podcast")
                        if c.isalnum() or c in (" ", "-", "_")
                    ).rstrip()
                    filename = (
                        f"{safe_title}.wav" if safe_title else f"podcast-{job.id}.wav"
                    )

                files.append(
                    {
                        "filename": filename,
                        "download_url": f"/api/v1/podcasts/{job.id}/audio/",
                    }
                )

            return Response({"files": files})
        except Exception as e:
            logger.error(f"Error listing podcast files for {podcast_id}: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
