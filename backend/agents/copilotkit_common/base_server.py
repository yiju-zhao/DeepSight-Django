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

    # Get environment settings
    frontend_port = os.getenv("FRONTEND_PORT", "5173")
    django_port = os.getenv("BACKEND_PORT", "8000")
    host_ip = os.getenv("HOST_IP", "localhost")
    environment = os.getenv("DJANGO_ENVIRONMENT", "development")

    # Build allowed origins
    # We must be specific if allow_credentials=True
    allowed_origins = [
        f"http://localhost:{frontend_port}",
        f"http://127.0.0.1:{frontend_port}",
        f"http://{host_ip}:{frontend_port}",
        f"http://localhost:{django_port}",
        f"http://127.0.0.1:{django_port}",
        f"http://{host_ip}:{django_port}",
    ]

    # In development, add more common local IPs or allow dynamic origin if needed
    if environment == "development":
        # Add common local network origins if HOST_IP is not set correctly
        # Note: We still can't use "*" with allow_credentials=True
        extra_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://0.0.0.0:5173",
        ]
        for origin in extra_origins:
            if origin not in allowed_origins:
                allowed_origins.append(origin)

    # Add CORS middleware with credentials support for session cookies
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"http://(10|172|192)\.\d+\.\d+\.\d+:5173"
        if environment == "development"
        else None,
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
