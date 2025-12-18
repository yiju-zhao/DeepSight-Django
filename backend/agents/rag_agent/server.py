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
from fastapi.responses import JSONResponse, StreamingResponse

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
from agents.rag_agent.graph import DeepSightRAGAgent
from agents.rag_agent.config import RAGAgentConfig
from agents.rag_agent.tools import create_mcp_retrieval_tools

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

    if request.url.path.startswith("/copilotkit"):
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
        self.name = "rag_assistant"
        self.id = "rag_assistant"  # Required for AG-UI protocol /info
        self.description = "RAG assistant for notebook documents"

    async def run(self, input_data: dict[str, Any]):
        """
        Main entry point for ag-ui-langgraph.
        Returns an async generator of events.
        """
        logger.info(f"DynamicRAGAgent.run received input_data type: {type(input_data)}")
        logger.info(f"input_data: {input_data}")

        req = current_request.get()
        if req is None:
            raise HTTPException(status_code=500, detail="Request context unavailable")

        # Extract notebook_id
        if hasattr(input_data, "configurable"):
            configurable = getattr(input_data, "configurable", {})
        elif isinstance(input_data, dict):
            configurable = input_data.get("configurable", {})
        else:
            configurable = {}

        logger.info(f"Extracted configurable: {configurable}")
        
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
            logger.info(f"Tried metadata, found notebook_id: {notebook_id}")

        if not notebook_id:
            # Last ditch effort: search the whole input_data if it's a dict
            if isinstance(input_data, dict):
                notebook_id = input_data.get("notebook_id")
                logger.info(f"Tried top-level, found notebook_id: {notebook_id}")

        if not notebook_id:
            logger.error(f"notebook_id still missing in input_data: {input_data}")
            raise HTTPException(status_code=400, detail="notebook_id missing")

        user_id = request_user_id = getattr(req.state, "user_id", None)
        
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

        # Wrap in LangGraphAGUIAgent for protocol compliance
        aguiaagent = LangGraphAGUIAgent(
            name=self.name,
            description=f"RAG assistant for notebook {notebook_id}",
            graph=self.agent.graph,
        )

        # Merge tools into config
        run_config = {
            "configurable": {
                **configurable,
                "retrieval_tools": retrieval_tools,
                "notebook_id": notebook_id,
                "user_id": user_id,
            }
        }

        # STREAM events from the agent
        async for event in aguiaagent.run(input_data, config=run_config):
            yield event


# Add the CopilotKit endpoint using corrected wrapper
add_langgraph_fastapi_endpoint(
    app=app,
    agent=DynamicRAGAgent(rag_agent),
    path="/copilotkit/internal",
)


@app.post("/copilotkit")
async def copilotkit_proxy(request: Request):
    """Proxy to handle AG-UI protocol routing and session forwarding."""
    try:
        payload = await request.json()
        logger.info(f"copilotkit_proxy received payload: {payload}")
        method = payload.get("method")
        inner_body = payload.get("body", {})


        # Extract forwardedProps from the body (CopilotKit's protocol)
        forwarded_props = inner_body.get("forwardedProps", {})
        
        # Also check for top-level properties (older protocol)
        top_level_props = payload.get("properties", {})
        
        # Merge both into configurable
        if forwarded_props or top_level_props:
            if "configurable" not in inner_body:
                inner_body["configurable"] = {}
            
            # Priority: forwardedProps > top-level properties
            inner_body["configurable"].update(top_level_props)
            inner_body["configurable"].update(forwarded_props)
            
            logger.info(f"Merged props into configurable: {inner_body['configurable']}")

        # Forward to internal endpoint
        forward_url = f"http://127.0.0.1:{RAG_AGENT_PORT}/copilotkit/internal"
        
        # Use follow_redirects=True if needed, but here we just stream
        async with httpx.AsyncClient(timeout=None) as client:
            # Forward cookies for authentication
            async with client.stream(
                "POST",
                forward_url,
                json=inner_body,
                cookies=request.cookies,
                headers={"Content-Type": "application/json"},
            ) as forward_resp:
                
                async def iter_bytes():
                    try:
                        async for chunk in forward_resp.aiter_raw():
                            yield chunk
                    except Exception as e:
                        logger.error(f"Stream error: {e}")
                
                # Filter out headers that shouldn't be copied for streaming responses
                response_headers = dict(forward_resp.headers)
                # Remove Content-Length as we're streaming and it may not match
                response_headers.pop('content-length', None)
                response_headers.pop('Content-Length', None)
                # Transfer-Encoding is handled by FastAPI/Starlette
                response_headers.pop('transfer-encoding', None)
                response_headers.pop('Transfer-Encoding', None)
                
                return StreamingResponse(
                    iter_bytes(),
                    status_code=forward_resp.status_code,
                    headers=response_headers,
                )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to forward CopilotKit request: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "Failed to forward CopilotKit request"},
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
