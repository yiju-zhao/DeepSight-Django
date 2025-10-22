from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse, HttpResponse, FileResponse
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
import logging
import json
import time
import redis
from django.conf import settings

from .models import Podcast
from .serializers import (
    PodcastSerializer,
    PodcastListSerializer,
    PodcastCreateSerializer,
)
from notebooks.models import Notebook

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
            qs = Podcast.objects.filter(user=request.user)
            if notebook_id:
                notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=notebook_id)
                qs = qs.filter(notebook=notebook)

            jobs = qs.order_by('-created_at')
            serializer = PodcastListSerializer(jobs, many=True)

            response = Response(serializer.data)
            if jobs:
                last_modified = max(job.updated_at for job in jobs)
                response['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')

            has_active_jobs = any(job_data.get('status') in ['pending', 'generating'] for job_data in serializer.data)
            cache_timeout = 2 if has_active_jobs else 5
            response['Cache-Control'] = f'max-age={cache_timeout}, must-revalidate'
            return response
        except Exception as e:
            logger.error(f"Error listing podcast jobs: {e}")
            return Response({"error": f"Failed to list jobs: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            serializer = PodcastCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=serializer.validated_data["notebook"])

            source_file_ids = serializer.validated_data["source_file_ids"]
            title = serializer.validated_data.get("title", "Generated Podcast")
            description = serializer.validated_data.get("description", "")

            job = Podcast.objects.create(
                user=request.user,
                notebook=notebook,
                title=title,
                description=description,
                source_file_ids=source_file_ids,
                source_metadata={},
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
            return Response({"error": f"Failed to create podcast-job: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class PodcastJobDetailView(generics.RetrieveDestroyAPIView):
    """
    Canonical: Retrieve or delete a specific podcast job by job_id.
    Handles GET and DELETE requests for a podcast job.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PodcastSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'job_id'

    def get_queryset(self):
        """Ensure users can only access their own podcasts."""
        return Podcast.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        """
        Override to delete the associated audio file from MinIO before deleting the object.
        """
        if instance.audio_object_key:
            try:
                from notebooks.utils.storage import get_minio_backend
                minio_backend = get_minio_backend()
                minio_backend.delete_file(instance.audio_object_key)
                logger.info(f"Successfully deleted podcast audio file for job {instance.id}")
            except Exception as e:
                # Log the error but don't block the deletion of the database record
                logger.error(f"Error deleting podcast audio file for job {instance.id}: {e}")
        
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to add cache-control headers to the response.
        """
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            response = Response(status=status.HTTP_204_NO_CONTENT)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        except Exception as e:
            logger.error(f"Error deleting podcast job {kwargs.get(self.lookup_url_kwarg)}: {e}")
            # The default exception handler will return a 404 if get_object() fails
            # We add a generic handler for other potential errors during deletion.
            return Response({"error": f"Failed to delete job: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class PodcastJobCancelView(APIView):
    """Canonical: Cancel a podcast job by job_id"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, job_id):
        """Cancel and delete a running or pending podcast job"""
        try:
            job = get_object_or_404(Podcast.objects.filter(user=request.user), id=job_id)
            if job.status in ["pending", "generating"]:
                from .tasks import cancel_podcast_generation
                task_result = cancel_podcast_generation.delay(str(job.id))
                result = task_result.get(timeout=10)
                if result.get("status") == "cancelled":
                    job.refresh_from_db()

                    # Now delete the cancelled job
                    if job.status == "cancelled":
                        job.delete()
                        return Response({
                            "job_id": str(job_id),
                            "status": "cancelled_and_deleted",
                            "message": "Podcast has been cancelled and deleted successfully"
                        }, status=status.HTTP_200_OK)
                    else:
                        # Job was cancelled but not deleted
                        serializer = PodcastSerializer(job)
                        return Response({
                            "job_id": str(job_id),
                            "status": "cancelled_only",
                            "message": "Podcast was cancelled but not deleted",
                            "detail": serializer.data
                        }, status=status.HTTP_206_PARTIAL_CONTENT)
                else:
                    return Response({"error": result.get("message", "Failed to cancel job")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({"error": f"Cannot cancel job with status: {job.status}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error cancelling podcast job {job_id}: {e}")
            return Response({"error": f"Failed to cancel job: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class PodcastJobAudioView(APIView):
    """Canonical: Serve audio files for podcast jobs"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = get_object_or_404(Podcast.objects.filter(user=request.user), id=job_id)
            logger.info(f"Audio request for job {job_id}: status={job.status}, audio_object_key={job.audio_object_key}")
            if not job.audio_object_key:
                return Response({"error": "Audio file not available"}, status=status.HTTP_404_NOT_FOUND)
            # If client asks JSON, return stable backend URL to this endpoint
            if request.headers.get('Accept') == 'application/json':
                return Response({"audio_url": f"/api/v1/podcasts/jobs/{job_id}/audio/"})

            # Proxy the audio bytes through backend to avoid exposing MinIO directly
            try:
                from notebooks.utils.storage import get_minio_backend
                minio_backend = get_minio_backend()
                iterator, length, ctype = minio_backend.stream_file(job.audio_object_key)
                if iterator is None:
                    return Response({"error": "Audio file not accessible"}, status=status.HTTP_404_NOT_FOUND)
                # Serve inline audio (streaming)
                resp = StreamingHttpResponse(iterator, content_type=ctype or 'audio/wav')
                safe_title = "".join(c for c in (job.title or "podcast") if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f"{safe_title}.wav" if safe_title else f"podcast-{job.id}.wav"
                resp["Content-Disposition"] = f'inline; filename="{filename}"'
                if length:
                    resp["Content-Length"] = str(length)
                # Caching hints (short-lived)
                resp["Cache-Control"] = 'max-age=60, must-revalidate'
                return resp
            except Exception as e:
                logger.error(f"Error proxying audio for job {job_id}: {e}")
                return Response({"error": f"Failed to read audio: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error serving audio for job {job_id}: {e}")
            return Response({"error": f"Failed to serve audio: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class PodcastJobDownloadView(APIView):
    """Canonical: Download audio files for podcast jobs"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = get_object_or_404(Podcast.objects.filter(user=request.user), id=job_id)
            logger.info(f"Download request for job {job_id}: status={job.status}, audio_object_key={job.audio_object_key}")
            if not job.audio_object_key:
                return Response({"error": "Audio file not available"}, status=status.HTTP_404_NOT_FOUND)
            try:
                from notebooks.utils.storage import get_minio_backend
                minio_backend = get_minio_backend()
                iterator, length, ctype = minio_backend.stream_file(job.audio_object_key)
                if iterator is None:
                    return Response({"error": "Audio file not accessible"}, status=status.HTTP_404_NOT_FOUND)
                # Prepare filename
                safe_title = "".join(c for c in (job.title or "podcast") if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f"{safe_title}.wav" if safe_title else f"podcast-{job.id}.wav"
                # Serve as attachment (streaming)
                response = StreamingHttpResponse(iterator, content_type=ctype or 'audio/wav')
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                if length:
                    response["Content-Length"] = str(length)
                response["Cache-Control"] = 'no-cache, no-store, must-revalidate'
                return response
            except Exception as e:
                logger.error(f"Error streaming download for job {job_id}: {e}")
                return Response({"error": f"Failed to stream download: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error downloading audio for job {job_id}: {e}")
            return Response({"error": f"Failed to download audio: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


def podcast_job_status_stream(request, job_id):
    """Canonical SSE endpoint for podcast job status by job_id"""
    if request.method == "OPTIONS":
        response = HttpResponse(status=200)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Authorization"
        response["Access-Control-Allow-Credentials"] = "true"
        return response


# ==============================
# Report-style views (no 'jobs')
# ==============================

class PodcastListCreateView(PodcastJobListCreateView):
    pass


class PodcastDetailView(PodcastJobDetailView):
    lookup_url_kwarg = 'podcast_id'


class PodcastCancelView(PodcastJobCancelView):
    def post(self, request, podcast_id):
        return super().post(request, job_id=podcast_id)


class PodcastAudioContentView(PodcastJobAudioView):
    def get(self, request, podcast_id):
        return super().get(request, job_id=podcast_id)


class PodcastAudioDownloadView(PodcastJobDownloadView):
    def get(self, request, podcast_id):
        return super().get(request, job_id=podcast_id)

    if not request.user.is_authenticated:
        response = StreamingHttpResponse(
            f"data: {json.dumps({'type': 'error', 'message': 'Authentication required'})}\n\n",
            content_type="text/event-stream",
            status=401,
        )
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    try:
        if not Podcast.objects.filter(id=job_id, user=request.user).exists():
            response = StreamingHttpResponse(
                f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n",
                content_type="text/event-stream",
                status=404,
            )
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Credentials"] = "true"
            return response

        redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)

        def event_stream():
            last_status = None
            max_duration = 3600
            start_time = time.time()
            poll_interval = 2

            while time.time() - start_time < max_duration:
                try:
                    current_job = Podcast.objects.filter(id=job_id, user=request.user).first()
                    if not current_job:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
                        break

                    cached_status = redis_client.get(f"podcast_job_status:{job_id}")
                    if cached_status:
                        status_data = json.loads(cached_status.decode("utf-8"))
                    else:
                        status_data = {
                            "job_id": str(current_job.id),
                            "status": current_job.status,
                            "progress": current_job.progress,
                            "error_message": current_job.error_message,
                            "audio_file_url": current_job.get_audio_url(),
                            "title": current_job.title,
                        }

                    current_status_str = json.dumps(status_data, sort_keys=True)
                    if current_status_str != last_status:
                        yield f"data: {json.dumps({'type': 'job_status', 'data': status_data})}\n\n"
                        last_status = current_status_str

                    if status_data["status"] in ["completed", "error", "cancelled"]:
                        break

                    time.sleep(poll_interval)

                except Exception as e:
                    logger.error(f"Error in SSE stream for job {job_id}: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    break

            yield f"data: {json.dumps({'type': 'stream_closed'})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control"
        response["Access-Control-Allow-Credentials"] = "true"
        return response
    except Exception as e:
        logger.error(f"Error setting up canonical SSE stream for job {job_id}: {e}")
        response = StreamingHttpResponse(
            f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n",
            content_type="text/event-stream",
        )
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"
        return response
