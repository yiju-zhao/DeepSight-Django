"""
Base FastAPI server factory for CopilotKit agents.

Provides a standardized way to create FastAPI applications with:
- CORS configuration for frontend and Django communication
- Health check endpoints
- Common middleware
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_agent_server(title: str, port: int) -> FastAPI:
    """
    Create a FastAPI application with standard configuration.
    
    Args:
        title: Service title for OpenAPI docs
        port: Port number the service will run on
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        description=f"CopilotKit agent service running on port {port}",
        version="1.0.0",
    )
    
    # Get allowed origins from environment or use defaults
    frontend_port = os.getenv("FRONTEND_PORT", "5173")
    django_port = os.getenv("BACKEND_PORT", "8000")
    host_ip = os.getenv("HOST_IP", "localhost")
    
    allowed_origins = [
        f"http://localhost:{frontend_port}",
        f"http://{host_ip}:{frontend_port}",
        f"http://localhost:{django_port}",
        f"http://{host_ip}:{django_port}",
    ]
    
    # Add CORS middleware with credentials support for session cookies
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,  # Required for session cookies
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health():
        """Health check endpoint for monitoring."""
        return {
            "status": "ok",
            "service": title,
            "port": port,
        }
    
    return app
