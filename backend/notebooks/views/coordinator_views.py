"""
Coordinator Views for Studio Integration

This module provides API endpoints for the Coordinator agent system,
enabling Studio mode functionality in the frontend.

Endpoints:
- POST /notebooks/{id}/studio/execute/    - Execute task with SSE streaming
- GET  /notebooks/{id}/studio/tasks/      - List studio tasks
- GET  /notebooks/{id}/studio/tasks/{id}/ - Get task details
- POST /notebooks/{id}/studio/tasks/{id}/respond/ - Respond to clarification
- DELETE /notebooks/{id}/studio/tasks/{id}/ - Cancel task
"""

import json
import logging
import time
import uuid
from typing import Generator

from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import View

from rest_framework import viewsets, serializers, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Notebook
from core.permissions import IsNotebookOwner


logger = logging.getLogger(__name__)


# ============================================================================
# SERIALIZERS
# ============================================================================


class TaskOptionsSerializer(serializers.Serializer):
    """Options for task execution."""

    style = serializers.ChoiceField(
        choices=["academic", "casual", "technical", "business"],
        default="academic",
        required=False,
    )
    max_research_iterations = serializers.IntegerField(
        min_value=1, max_value=20, required=False
    )
    timeout = serializers.FloatField(
        min_value=60,
        max_value=1800,  # 1 min to 30 min
        required=False,
    )
    skip_clarification = serializers.BooleanField(default=False, required=False)


class ExecuteTaskSerializer(serializers.Serializer):
    """Request serializer for task execution."""

    goal = serializers.CharField(
        max_length=5000, help_text="The user's research goal or question"
    )
    options = TaskOptionsSerializer(required=False)


class ClarificationResponseSerializer(serializers.Serializer):
    """Request serializer for responding to clarification."""

    response = serializers.CharField(
        max_length=2000, help_text="User's response to clarification questions"
    )


class TaskSerializer(serializers.Serializer):
    """Task response serializer."""

    task_id = serializers.CharField()
    status = serializers.CharField()
    goal = serializers.CharField()
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)
    result_summary = serializers.CharField(allow_null=True)


# ============================================================================
# TASK STORAGE (In-memory for now, could be moved to database)
# ============================================================================

# In-memory task storage - in production, use database model
_active_tasks = {}


class TaskState:
    """Represents an active task state."""

    def __init__(self, task_id: str, notebook_id: str, goal: str, options: dict = None):
        self.task_id = task_id
        self.notebook_id = notebook_id
        self.goal = goal
        self.options = options or {}
        self.status = "pending"
        self.created_at = time.time()
        self.completed_at = None
        self.result = None
        self.error = None
        self.clarification_questions = []
        self.clarification_responses = []
        self.coordinator = None

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "notebook_id": self.notebook_id,
            "goal": self.goal,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "has_result": self.result is not None,
            "error": self.error,
        }


def get_task(task_id: str) -> TaskState:
    """Get task by ID."""
    return _active_tasks.get(task_id)


def save_task(task: TaskState):
    """Save task to storage."""
    _active_tasks[task.task_id] = task


def delete_task(task_id: str):
    """Delete task from storage."""
    _active_tasks.pop(task_id, None)


# ============================================================================
# SSE STREAMING HELPERS
# ============================================================================


def sse_event(event_type: str, data: dict) -> str:
    """Format an SSE event."""
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


def sse_error(message: str) -> str:
    """Format an SSE error event."""
    return sse_event("error", {"message": message})


def sse_done(data: dict = None) -> str:
    """Format an SSE done event."""
    return sse_event("done", data or {})


# ============================================================================
# COORDINATOR VIEW SET
# ============================================================================


class CoordinatorViewSet(viewsets.ViewSet):
    """
    ViewSet for Coordinator task operations.

    Provides endpoints for:
    - Creating and executing research/writing tasks
    - Handling multi-turn clarification
    - Streaming task progress via SSE
    - Retrieving task results
    """

    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]

    def get_notebook(self, request, notebook_pk: str) -> Notebook:
        """Get notebook with ownership validation."""
        return get_object_or_404(
            Notebook.objects.filter(user=request.user), pk=notebook_pk
        )

    def list(self, request, notebook_pk=None):
        """List all tasks for a notebook."""
        notebook = self.get_notebook(request, notebook_pk)

        # Filter tasks for this notebook
        tasks = [
            task.to_dict()
            for task in _active_tasks.values()
            if task.notebook_id == str(notebook.id)
        ]

        # Sort by created_at descending
        tasks.sort(key=lambda t: t["created_at"], reverse=True)

        return Response({"success": True, "tasks": tasks, "count": len(tasks)})

    def retrieve(self, request, notebook_pk=None, pk=None):
        """Get task details."""
        notebook = self.get_notebook(request, notebook_pk)
        task = get_task(pk)

        if not task or task.notebook_id != str(notebook.id):
            return Response(
                {"detail": "Task not found"}, status=status.HTTP_404_NOT_FOUND
            )

        response_data = task.to_dict()

        # Include result if completed
        if task.result:
            response_data["result"] = {
                "findings": task.result.get("findings"),
                "final_report": task.result.get("final_report"),
                "sources": task.result.get("sources", []),
            }

        return Response({"success": True, "task": response_data})

    def destroy(self, request, notebook_pk=None, pk=None):
        """Cancel/delete a task."""
        notebook = self.get_notebook(request, notebook_pk)
        task = get_task(pk)

        if not task or task.notebook_id != str(notebook.id):
            return Response(
                {"detail": "Task not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Update status and remove
        task.status = "cancelled"
        delete_task(pk)

        logger.info(f"Task {pk} cancelled for notebook {notebook.id}")

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="respond")
    def respond_to_clarification(self, request, notebook_pk=None, pk=None):
        """Respond to clarification questions."""
        notebook = self.get_notebook(request, notebook_pk)
        task = get_task(pk)

        if not task or task.notebook_id != str(notebook.id):
            return Response(
                {"detail": "Task not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if task.status != "clarifying":
            return Response(
                {"detail": "Task is not awaiting clarification"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ClarificationResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response_text = serializer.validated_data["response"]
        task.clarification_responses.append(response_text)

        logger.info(f"Received clarification response for task {pk}")

        return Response({"success": True, "message": "Response received"})


# ============================================================================
# SSE EXECUTION VIEW
# ============================================================================


class StudioExecuteSSEView(View):
    """
    SSE endpoint for executing coordinator tasks with streaming progress.

    POST /notebooks/{notebook_id}/studio/execute/

    Request body:
        {
            "goal": "Research LLM agents and write a report",
            "options": {
                "style": "academic",
                "skip_clarification": false
            }
        }

    SSE Response events:
        - type: "started" - Task started
        - type: "clarification" - Clarification questions
        - type: "progress" - Task progress update
        - type: "result" - Partial or final result
        - type: "done" - Task completed
        - type: "error" - Error occurred
    """

    @method_decorator(csrf_exempt)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def options(self, request, notebook_id: str):
        """Handle CORS preflight."""
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "Accept, Authorization, Content-Type, X-CSRFToken"
        )
        return response

    def post(self, request, notebook_id: str):
        """Execute a coordinator task with SSE streaming."""
        try:
            # Validate notebook ownership
            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_id
            )

            # Parse request body
            try:
                body = json.loads(request.body)
            except json.JSONDecodeError:
                return HttpResponse(
                    "Invalid JSON", status=400, content_type="text/plain"
                )

            # Validate request
            serializer = ExecuteTaskSerializer(data=body)
            if not serializer.is_valid():
                return HttpResponse(
                    json.dumps({"errors": serializer.errors}),
                    status=400,
                    content_type="application/json",
                )

            goal = serializer.validated_data["goal"]
            options = serializer.validated_data.get("options", {})

            # Create task
            task_id = str(uuid.uuid4())
            task = TaskState(
                task_id=task_id,
                notebook_id=str(notebook.id),
                goal=goal,
                options=options,
            )
            save_task(task)

            logger.info(
                f"Starting task {task_id} for notebook {notebook.id}: {goal[:100]}"
            )

            # Create streaming response
            response = StreamingHttpResponse(
                self.generate_execution_stream(task, notebook),
                content_type="text/event-stream",
            )
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Headers"] = (
                "Accept, Authorization, Content-Type"
            )
            response["Access-Control-Allow-Methods"] = "POST, OPTIONS"

            return response

        except Exception as e:
            logger.exception(f"Failed to start task execution: {e}")
            return HttpResponse(
                f"Error: {str(e)}", status=500, content_type="text/plain"
            )

    def generate_execution_stream(
        self, task: TaskState, notebook: Notebook
    ) -> Generator[str, None, None]:
        """
        Generate SSE stream for task execution.

        This is a simplified implementation that simulates the coordinator.
        In production, this would call the actual Coordinator agent.
        """
        import asyncio

        try:
            task.status = "executing"

            # Send started event
            yield sse_event("started", {"task_id": task.task_id, "goal": task.goal})

            # Import coordinator
            try:
                from agents.coordinator import execute_task
                from agents.coordinator.schema import TaskOptions, TaskType
            except ImportError as e:
                logger.warning(f"Coordinator not available: {e}")
                # Fallback to simulation mode
                yield from self._simulate_execution(task)
                return

            # Build task options
            options = TaskOptions(
                style=task.options.get("style", "academic"),
                skip_clarification=task.options.get("skip_clarification", False),
                max_research_iterations=task.options.get("max_research_iterations"),
                timeout=task.options.get("timeout"),
            )

            # Progress callback for SSE updates
            last_update_time = time.time()

            # Send progress updates
            yield sse_event(
                "progress",
                {
                    "step": "research",
                    "status": "starting",
                    "message": "Starting research...",
                },
            )

            # Execute coordinator task
            try:
                # Run async coordinator in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    result = loop.run_until_complete(execute_task(task.goal, options))
                finally:
                    loop.close()

                # Process result
                if result.status.value == "completed":
                    task.status = "completed"
                    task.completed_at = time.time()
                    task.result = {
                        "findings": result.findings,
                        "final_report": result.final_report,
                        "sources": result.sources,
                    }

                    yield sse_event(
                        "result",
                        {
                            "task_id": task.task_id,
                            "findings": result.findings[:500]
                            if result.findings
                            else None,
                            "report_preview": result.final_report[:1000]
                            if result.final_report
                            else None,
                            "source_count": len(result.sources)
                            if result.sources
                            else 0,
                        },
                    )

                    yield sse_done({"task_id": task.task_id, "status": "completed"})

                else:
                    task.status = "failed"
                    task.error = result.error_message

                    yield sse_error(result.error_message or "Task failed")

            except Exception as e:
                logger.exception(f"Coordinator execution failed: {e}")
                task.status = "failed"
                task.error = str(e)
                yield sse_error(str(e))

        except GeneratorExit:
            logger.info(f"Client disconnected from task {task.task_id}")
            task.status = "cancelled"

        except Exception as e:
            logger.exception(f"Error in execution stream: {e}")
            yield sse_error(str(e))

        finally:
            save_task(task)

    def _simulate_execution(self, task: TaskState) -> Generator[str, None, None]:
        """
        Simulate execution when coordinator is not available.
        Used for development/testing.
        """
        import time

        # Simulate clarification
        if not task.options.get("skip_clarification"):
            yield sse_event(
                "clarification",
                {
                    "task_id": task.task_id,
                    "questions": [
                        {
                            "question": "What specific aspects would you like me to focus on?",
                            "purpose": "To narrow down the research scope",
                            "required": False,
                        }
                    ],
                    "message": "I have a few clarifying questions before proceeding.",
                },
            )

            # Wait briefly for response (in real impl, would wait for user)
            time.sleep(1)

        # Simulate research progress
        yield sse_event(
            "progress",
            {
                "step": "research",
                "status": "running",
                "message": "Conducting web research...",
            },
        )
        time.sleep(2)

        yield sse_event(
            "progress",
            {
                "step": "research",
                "status": "completed",
                "message": "Research completed",
            },
        )

        # Simulate writing progress
        yield sse_event(
            "progress",
            {"step": "writing", "status": "running", "message": "Generating report..."},
        )
        time.sleep(2)

        # Simulate result
        task.status = "completed"
        task.completed_at = time.time()
        task.result = {
            "findings": f"Research findings for: {task.goal}",
            "final_report": f"# Report\n\nThis is a simulated report for: {task.goal}\n\n## Key Findings\n\n- Finding 1\n- Finding 2\n- Finding 3",
            "sources": [
                {"url": "https://example.com/1", "title": "Example Source 1"},
                {"url": "https://example.com/2", "title": "Example Source 2"},
            ],
        }

        yield sse_event(
            "result",
            {
                "task_id": task.task_id,
                "findings": task.result["findings"],
                "report_preview": task.result["final_report"][:500],
                "source_count": len(task.result["sources"]),
            },
        )

        yield sse_done({"task_id": task.task_id, "status": "completed"})
