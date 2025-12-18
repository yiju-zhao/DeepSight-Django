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
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse, Response

# Setup Django before other imports
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django
django.setup()

# Import CopilotKit SDK components
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from agents.copilotkit_common.base_server import create_agent_server
from agents.copilotkit_common.utils import get_openai_api_key, get_mcp_server_url

# RAG agent imports
from agents.rag_agent.graph import DeepSightRAGAgent
from agents.rag_agent.config import RAGAgentConfig
from agents.rag_agent.tools import create_mcp_retrieval_tools
from agents.rag_agent.context import current_retrieval_tools

logger = logging.getLogger(__name__)

# Agent port configuration
RAG_AGENT_PORT = int(os.getenv("RAG_AGENT_PORT", "8101"))

# Create FastAPI application with CORS and health check
app = create_agent_server("RAG Agent Service", RAG_AGENT_PORT)

# Track the current request for dynamic context
current_request: ContextVar[Request | None] = ContextVar("current_request", default=None)

# Initialize the base configuration (we'll override specific values per request)
# We don't have the API key yet, we'll get it from the utility
base_config = RAGAgentConfig(
    model_name=os.getenv("RAG_AGENT_MODEL", "gpt-4o-mini"),
    api_key=get_openai_api_key(),
    dataset_ids=[], # Initial empty, will be set per request
    mcp_server_url=get_mcp_server_url(),
)

# Initialize the agent once
rag_agent = DeepSightRAGAgent(base_config)


async def validate_django_session_middleware(request: Request, call_next):
    """Middleware to validate Django session and inject user_id."""
    if request.method == "OPTIONS":
        return await call_next(request)

    # Allow all /copilotkit requests through - DynamicRAGAgent.run() will handle auth
    # The /info endpoint provided by LangGraph needs to be public for agent discovery
    if request.url.path.startswith("/copilotkit"):
        # Store request context for DynamicRAGAgent.run() to access
        current_request.set(request)
        response = await call_next(request)
        current_request.set(None)
        return response

    # For other paths, require session authentication
    if request.url.path.startswith("/api"):
        session_cookie = request.cookies.get("sessionid")

        if not session_cookie:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        from django.contrib.sessions.backends.db import SessionStore
        from django.contrib.auth import get_user_model
        from asgiref.sync import sync_to_async

        User = get_user_model()
        session = SessionStore(session_key=session_cookie)

        @sync_to_async
        def get_auth_user_id(session_store, cookie):
            if not session_store.exists(cookie):
                return None
            return session_store.get("_auth_user_id")

        user_id = await get_auth_user_id(session, session_cookie)

        if not user_id:
            return JSONResponse(status_code=401, content={"detail": "Invalid session"})

        try:
            user = await User.objects.aget(pk=user_id, is_active=True)
            request.state.user_id = user.pk
        except User.DoesNotExist:
            return JSONResponse(status_code=401, content={"detail": "User not active"})

        # Pass request context
        current_request.set(request)

    response = await call_next(request)
    current_request.set(None)
    return response


app.middleware("http")(validate_django_session_middleware)


class DynamicRAGAgent:
    """
    Adapter for ag-ui-langgraph that handles per-request setup.
    """
    def __init__(self, agent: DeepSightRAGAgent):
        self.agent = agent
        self.name = "rag_agent"
        self.id = "rag_agent"  # Required for AG-UI protocol /info
        self.description = "RAG agent for notebook documents"

    async def run(self, input_data: dict[str, Any]):
        """
        Main entry point for ag-ui-langgraph.
        Returns an async generator of events.
        """
        req = current_request.get()
        if req is None:
            raise HTTPException(status_code=500, detail="Request context unavailable")

        # Authenticate the request - /info requests won't reach here, only actual agent runs
        session_cookie = req.cookies.get("sessionid")
        if not session_cookie:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Validate Django session
        from django.contrib.sessions.backends.db import SessionStore
        from asgiref.sync import sync_to_async

        session = SessionStore(session_key=session_cookie)

        @sync_to_async
        def get_auth_user_id(session_store, cookie):
            if not session_store.exists(cookie):
                return None
            return session_store.get("_auth_user_id")

        user_id = await get_auth_user_id(session, session_cookie)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session")

        # Extract notebook_id
        if hasattr(input_data, "configurable"):
            configurable = getattr(input_data, "configurable", {})
        elif isinstance(input_data, dict):
            configurable = input_data.get("configurable", {})
        else:
            configurable = {}

        notebook_id = configurable.get("notebook_id")
        if not notebook_id:
            # Try to see if it's in metadata
            if hasattr(input_data, "metadata"):
                metadata = getattr(input_data, "metadata", {})
            elif isinstance(input_data, dict):
                metadata = input_data.get("metadata", {})
            else:
                metadata = {}
            notebook_id = metadata.get("notebook_id")

        if not notebook_id:
            # Last ditch effort: search the whole input_data if it's a dict
            if isinstance(input_data, dict):
                notebook_id = input_data.get("notebook_id")

        if not notebook_id:
            logger.error(f"notebook_id still missing in input_data: {input_data}")
            raise HTTPException(status_code=400, detail="notebook_id missing")

        # Check for empty message list (initial connection/warm-up)
        # If messages are empty, we should not run the graph as it would trigger an empty question flow
        messages = []
        if isinstance(input_data, dict):
            messages = input_data.get("messages", [])
        elif hasattr(input_data, "messages"):
            messages = getattr(input_data, "messages", [])
            
        if not messages:
            logger.info("Empty message list received, skipping graph execution")
            return

        # user_id already authenticated above
        # Load notebook configuration asynchronously
        from notebooks.models import Notebook
        try:
            notebook = await Notebook.objects.aget(id=notebook_id, user_id=user_id)
        except Notebook.DoesNotExist:
            raise HTTPException(status_code=404, detail="Notebook not found")

        dataset_ids = [notebook.ragflow_dataset_id] if notebook.ragflow_dataset_id else []
        
        # Create tools for this specific request
        retrieval_tools = await create_mcp_retrieval_tools(
            dataset_ids=dataset_ids,
            mcp_server_url=self.agent.config.mcp_server_url
        )

        # Store tools in context variable (NOT in config to avoid serialization issues)
        current_retrieval_tools.set(retrieval_tools)

        # Wrap in LangGraphAGUIAgent for protocol compliance
        aguiaagent = LangGraphAGUIAgent(
            name=self.name,
            description=f"RAG assistant for notebook {notebook_id}",
            graph=self.agent.graph,
        )

        # Merge the configuration into input_data's configurable
        # LangGraph expects config in input_data, not as a separate parameter
        # IMPORTANT: Do NOT include retrieval_tools here - they cause circular reference errors
        if isinstance(input_data, dict):
            if "configurable" not in input_data:
                input_data["configurable"] = {}

            # Merge our config with existing configurable (WITHOUT tools)
            input_data["configurable"].update({
                **configurable,
                "notebook_id": notebook_id,
                "user_id": user_id,
            })
        else:
            # If input_data is an object with configurable attribute
            if not hasattr(input_data, "configurable"):
                input_data.configurable = {}
            input_data.configurable.update({
                **configurable,
                "notebook_id": notebook_id,
                "user_id": user_id,
            })

        # STREAM events from the agent
        try:
            async for event in aguiaagent.run(input_data):
                yield event
        finally:
            # Cleanup context variable
            current_retrieval_tools.set(None)


# Add the LangGraph endpoint at /copilotkit/ag-ui (internal path)
add_langgraph_fastapi_endpoint(
    app=app,
    agent=DynamicRAGAgent(rag_agent),
    path="/copilotkit/ag-ui",
)


@app.api_route("/copilotkit", methods=["GET", "POST"])
async def copilotkit_adapter(request: Request):
    """
    Lightweight adapter for CopilotKit protocol.
    Handles /info requests and forwards agent requests to AG-UI endpoint.
    """
    # Handle GET requests (agent discovery)
    if request.method == "GET":
        return JSONResponse({
            "agents": {
                "rag_agent": {
                    "id": "rag_agent",
                    "name": "rag_agent",
                    "description": "RAG agent for notebook documents",
                    "agentType": "langgraph",
                }
            }
        })

    # Handle POST requests
    try:
        payload = await request.json()
        method = payload.get("method")

        # Handle /info method (agent discovery)
        if method == "info":
            return JSONResponse({
                "agents": {
                    "rag_agent": {
                        "id": "rag_agent",
                        "name": "rag_agent",
                        "description": "RAG agent for notebook documents",
                        "agentType": "langgraph",
                    }
                }
            })

        # For all other requests, forward to the AG-UI endpoint
        # Extract the body content - AG-UI expects body directly, not wrapped
        inner_body = payload.get("body", {})

        # Merge forwardedProps into configurable for LangGraph
        forwarded_props = inner_body.get("forwardedProps", {})
        if forwarded_props:
            if "configurable" not in inner_body:
                inner_body["configurable"] = {}
            inner_body["configurable"].update(forwarded_props)

        forward_url = f"http://127.0.0.1:{RAG_AGENT_PORT}/copilotkit/ag-ui"

        # Use a client for streaming
        client = httpx.AsyncClient(timeout=None)
        try:
            req = client.build_request(
                "POST",
                forward_url,
                json=inner_body,
                cookies=request.cookies,
                headers={"Content-Type": "application/json"},
            )
            r = await client.send(req, stream=True)
        except Exception:
            await client.aclose()
            raise

        async def stream_response():
            try:
                async for chunk in r.aiter_raw():
                    yield chunk
            finally:
                await r.aclose()
                await client.aclose()

        # Return the response with proper headers
        # Filter out headers that might conflict with the new Response or have been handled by httpx
        headers = dict(r.headers)
        keys_to_remove = ["content-length", "transfer-encoding", "content-encoding", "connection"]
        for key in keys_to_remove:
            for h in list(headers.keys()):
                if h.lower() == key:
                    del headers[h]

        return StreamingResponse(
            stream_response(),
            status_code=r.status_code,
            headers=headers,
        )

    except Exception as exc:
        logger.exception("Adapter error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
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
