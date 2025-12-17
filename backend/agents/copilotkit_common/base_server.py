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
    django_port = os.getenv("BACKEND_PORT", "8001")
    host_ip = os.getenv("HOST_IP", "localhost")
    environment = os.getenv("DJANGO_ENVIRONMENT", "development")

    # Build allowed origins
    allowed_origins = [
        f"http://localhost:{frontend_port}",
        f"http://127.0.0.1:{frontend_port}",
        f"http://{host_ip}:{frontend_port}",
        f"http://localhost:{django_port}",
        f"http://127.0.0.1:{django_port}",
        f"http://{host_ip}:{django_port}",
    ]

    # In development, allow all origins for easier local development
    # This handles cases where frontend runs on different IPs (e.g., 10.x.x.x, 192.168.x.x)
    if environment == "development":
        allowed_origins = ["*"]
        print(f"⚠️  CORS: Allowing all origins in development mode")
    else:
        print(f"✓ CORS: Allowing origins: {allowed_origins}")

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
