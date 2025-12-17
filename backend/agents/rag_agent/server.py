"""
FastAPI server for RAG Agent with CopilotKit AG-UI protocol.

Provides the RAG agent as a CopilotKit-compatible endpoint that:
- Validates Django session authentication
- Creates notebook-specific agent instances
- Streams agent state updates via AG-UI protocol

Usage:
    cd backend && python -m agents.rag_agent.server

Or with uvicorn:
    cd backend && uvicorn agents.rag_agent.server:app --port 8002 --reload
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import Depends, Request
from fastapi.responses import StreamingResponse

# Setup Django before other imports
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.development")

import django
django.setup()

from agents.copilotkit_common.auth import verify_django_session, get_notebook_config
from agents.copilotkit_common.base_server import create_agent_server
from agents.copilotkit_common.utils import get_openai_api_key, get_mcp_server_url

# RAG agent imports
from agents.rag_agent.graph import create_rag_agent
from agents.rag_agent.config import RAGAgentConfig

logger = logging.getLogger(__name__)

# Agent port configuration
RAG_AGENT_PORT = int(os.getenv("RAG_AGENT_PORT", "8101"))

# Create FastAPI application
app = create_agent_server("RAG Agent Service", RAG_AGENT_PORT)


@app.post("/copilotkit/notebooks/{notebook_id}/agent")
async def rag_agent_endpoint(
    notebook_id: int,
    request: Request,
    user_id: int = Depends(verify_django_session),
):
    """
    CopilotKit-compatible RAG agent endpoint.
    
    This endpoint:
    1. Validates Django session authentication
    2. Loads notebook configuration with access control
    3. Creates a RAG agent instance for the notebook
    4. Streams responses using AG-UI protocol
    
    Args:
        notebook_id: Notebook primary key
        request: FastAPI request object
        user_id: Authenticated user ID from session
        
    Returns:
        Streaming response with AG-UI protocol events
    """
    logger.info(f"RAG agent request: notebook={notebook_id}, user={user_id}")
    
    # Load notebook with access validation
    notebook = await get_notebook_config(notebook_id, user_id)
    
    # Get request body for CopilotKit protocol
    body = await request.json()
    messages = body.get("messages", [])
    
    # Extract the latest user message
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break
    
    if not user_message:
        return {"error": "No user message found"}
    
    # Build dataset IDs from notebook
    dataset_ids = []
    if notebook.ragflow_dataset_id:
        dataset_ids = [notebook.ragflow_dataset_id]
    
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
    
    # Create and run agent
    agent = await create_rag_agent(config)
    
    async def generate_stream():
        """Generate AG-UI protocol events from agent execution."""
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Build message history
        context_messages = []
        for msg in messages[:-1]:  # Exclude current message
            if msg.get("role") == "user":
                context_messages.append(HumanMessage(content=msg.get("content", "")))
            else:
                context_messages.append(AIMessage(content=msg.get("content", "")))
        
        # Add current question
        context_messages.append(HumanMessage(content=user_message))
        
        # Initial state
        initial_state = {
            "messages": context_messages,
            "question": user_message,
            "retrieved_chunks": [],
        }
        
        try:
            # Stream agent execution
            async for event in agent.astream(initial_state):
                # Extract the final message if present
                if "messages" in event:
                    for msg in event["messages"]:
                        if hasattr(msg, "content") and msg.content:
                            # Yield content as AG-UI text delta
                            yield f"data: {{\n"
                            yield f'  "type": "text_delta",\n'
                            yield f'  "content": {repr(msg.content)}\n'
                            yield f"}}\n\n"
            
            # Signal completion
            yield f"data: {{\n"
            yield f'  "type": "done"\n'
            yield f"}}\n\n"
            
        except Exception as e:
            logger.exception(f"Agent execution error: {e}")
            yield f"data: {{\n"
            yield f'  "type": "error",\n'
            yield f'  "message": {repr(str(e))}\n'
            yield f"}}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting RAG Agent server on port {RAG_AGENT_PORT}")
    uvicorn.run(
        "agents.rag_agent.server:app",
        host="0.0.0.0",
        port=RAG_AGENT_PORT,
        reload=True,
    )
