"""
FastAPI server for RAG Agent with CopilotKit AG-UI protocol.

Refactored to use official CopilotKit Python SDK with LangGraphAGUIAgent
and add_langgraph_fastapi_endpoint for proper AG-UI protocol integration.

The agent supports notebook-specific RAG via configuration:
- Frontend passes notebook_id via CopilotKit properties prop
- LangGraph receives it via config["configurable"]["notebook_id"]
- Django session authentication validates access

Usage:
    cd backend && python -m agents.rag_agent.server

Or with uvicorn:
    cd backend && uvicorn agents.rag_agent.server:app --port 8101 --reload
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional, Callable, Awaitable

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Setup Django before other imports
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.development")

import django
django.setup()

# Import CopilotKit SDK components
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from agents.copilotkit_common.base_server import create_agent_server
from agents.copilotkit_common.utils import get_openai_api_key, get_mcp_server_url

# RAG agent imports
from agents.rag_agent.graph import create_rag_agent
from agents.rag_agent.config import RAGAgentConfig

logger = logging.getLogger(__name__)

# Agent port configuration
RAG_AGENT_PORT = int(os.getenv("RAG_AGENT_PORT", "8101"))

# Create FastAPI application with CORS and health check
app = create_agent_server("RAG Agent Service", RAG_AGENT_PORT)


class UnwrapCopilotKitEnvelopeMiddleware(BaseHTTPMiddleware):
    """
    CopilotKit (React) sends a JSON-RPC style envelope by default:
        { "method": "agent/connect", "params": {...}, "body": { ...actual payload... } }
    The `add_langgraph_fastapi_endpoint` helper expects the flat AG-UI payload at the
    top level, so we unwrap the `body` key before it reaches the endpoint.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Any]]):
        if request.url.path.startswith("/copilotkit"):
            try:
                raw_body = await request.body()
                if raw_body:
                    payload = json.loads(raw_body)
                    logger.info("CopilotKit envelope received: keys=%s", list(payload.keys()))
                    # Short-circuit the CopilotKit runtime info probe
                    if payload.get("method") == "info":
                        return JSONResponse(
                            {
                                "agents": [
                                    {
                                        "id": "rag_assistant",
                                        "name": "rag_assistant",
                                        "description": "Notebook RAG assistant",
                                    }
                                ]
                            }
                        )
                    if isinstance(payload, dict) and isinstance(payload.get("body"), dict):
                        inner = payload["body"]
                        new_body = json.dumps(inner).encode("utf-8")
                        logger.info("Unwrapped CopilotKit body keys=%s", list(inner.keys()))

                        async def receive() -> dict[str, Any]:
                            return {
                                "type": "http.request",
                                "body": new_body,
                                "more_body": False,
                            }

                        # Replace the request with the unwrapped body
                        request = Request(request.scope, receive=receive)
                        request._body = new_body  # type: ignore[attr-defined]
                    else:
                        # If there is no nested body, forward as-is (e.g., unexpected shapes)
                        async def receive_passthrough() -> dict[str, Any]:
                            return {
                                "type": "http.request",
                                "body": raw_body,
                                "more_body": False,
                            }

                        request = Request(request.scope, receive=receive_passthrough)
                        request._body = raw_body  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001 - defensive: never block request
                logger.warning("Failed to unwrap CopilotKit envelope: %s", exc)

        return await call_next(request)


async def create_notebook_rag_graph(notebook_id: Any, user_id: Any):
    """
    Create a notebook-specific RAG agent graph.

    This function:
    1. Validates notebook access for the user
    2. Loads notebook configuration (dataset IDs)
    3. Creates and returns a RAG graph for that notebook

    Args:
        notebook_id: Notebook primary key (UUID or int)
        user_id: Authenticated user ID (UUID or int)

    Returns:
        Compiled LangGraph for the notebook

    Raises:
        HTTPException: If notebook not found or access denied
    """
    from notebooks.models import Notebook

    try:
        # Load notebook with access validation
        notebook = await Notebook.objects.select_related("user").aget(
            id=notebook_id,
            user_id=user_id,
        )
    except Notebook.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found or access denied",
        )

    # Build dataset IDs from notebook
    dataset_ids = []
    if notebook.ragflow_dataset_id:
        dataset_ids = [notebook.ragflow_dataset_id]

    if not dataset_ids:
        logger.warning(f"Notebook {notebook_id} has no datasets configured")

    # Create agent configuration
    config = RAGAgentConfig(
        model_name=os.getenv("RAG_AGENT_MODEL", "gpt-4o-mini"),
        api_key=get_openai_api_key(),
        dataset_ids=dataset_ids,
        mcp_server_url=get_mcp_server_url(),
        max_iterations=5,
        temperature=0.7,
        eval_temperature=0.1,
        synthesis_temperature=0.3,
    )

    # Create and return RAG graph
    graph = await create_rag_agent(config)
    logger.info(f"Created RAG graph for notebook {notebook_id}")

    return graph


async def validate_django_session_middleware(request: Request, call_next):
    """
    Middleware to validate Django session for CopilotKit requests.

    Validates session cookies for all /copilotkit/* endpoints and injects
    user_id into request.state for downstream use.
    """
    # Skip validation for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.url.path.startswith("/copilotkit"):
        # Debug: Log all cookies and headers
        logger.info(f"Request cookies: {request.cookies.keys()}")
        logger.info(f"Session cookie present: {'sessionid' in request.cookies}")
        
        # Extract session cookie
        session_cookie = request.cookies.get("sessionid")

        if not session_cookie:
            logger.warning("Authentication failed: No session cookie found")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        # Validate session with Django
        from django.contrib.sessions.backends.db import SessionStore
        from django.contrib.auth import get_user_model
        from asgiref.sync import sync_to_async

        User = get_user_model()
        session = SessionStore(session_key=session_cookie)

        @sync_to_async
        def check_session_and_get_user(session_store, cookie):
            if not session_store.exists(cookie):
                return False, None
            return True, session_store.get("_auth_user_id")

        is_valid, user_id = await check_session_and_get_user(session, session_cookie)

        if not is_valid:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired session"},
            )

        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "User not authenticated"},
            )

        # Verify user exists and is active
        try:
            user = await User.objects.aget(pk=user_id, is_active=True)
            # Store user_id in request state for graph factory
            request.state.user_id = user.pk
        except User.DoesNotExist:
            return JSONResponse(
                status_code=401,
                content={"detail": "User not found or inactive"},
            )

    response = await call_next(request)
    return response


# Middleware order matters: unwrap the CopilotKit envelope first, then validate session
app.add_middleware(UnwrapCopilotKitEnvelopeMiddleware)
app.middleware("http")(validate_django_session_middleware)


async def agent_factory(request: Request, config: dict[str, Any]) -> LangGraphAGUIAgent:
    """
    Factory function to create notebook-specific RAG agents.

    This is called by add_langgraph_fastapi_endpoint for each request.
    The function receives configuration from the frontend CopilotKit provider
    (passed via properties prop) and creates an agent for that notebook.

    Args:
        request: FastAPI request object (contains user_id in request.state)
        config: Configuration dict from frontend with notebook_id

    Returns:
        LangGraphAGUIAgent instance for the notebook
    """
    # Extract notebook_id from config (passed from frontend)
    notebook_id = config.get("configurable", {}).get("notebook_id")

    if not notebook_id:
        raise HTTPException(
            status_code=400,
            detail="notebook_id is required in configuration",
        )

    # Get user_id from middleware
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User authentication failed",
        )

    logger.info(f"Creating agent for notebook {notebook_id}, user {user_id}")

    # Create notebook-specific graph
    graph = await create_notebook_rag_graph(
        notebook_id=notebook_id,
        user_id=user_id,
    )

    # Wrap in LangGraphAGUIAgent
    agent = LangGraphAGUIAgent(
        name="rag_assistant",
        description=f"Research assistant for notebook {notebook_id} that can query and synthesize information from your documents",
        graph=graph,
    )

    return agent


# Add the CopilotKit endpoint using official SDK
# This replaces the manual AG-UI protocol implementation
add_langgraph_fastapi_endpoint(
    app=app,
    agent=agent_factory,  # Pass factory function for per-request agent creation
    path="/copilotkit",
)

logger.info("RAG agent server initialized with CopilotKit SDK")


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting RAG Agent server on port {RAG_AGENT_PORT}")
    uvicorn.run(
        "agents.rag_agent.server:app",
        host="0.0.0.0",
        port=RAG_AGENT_PORT,
        reload=False,
    )
