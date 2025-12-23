"""
Django session authentication for CopilotKit FastAPI agents.

Provides shared authentication utilities that validate Django session cookies
and load notebook configurations with access control.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import Cookie, HTTPException, status


def setup_django():
    """
    Initialize Django settings for use in FastAPI context.

    Must be called before any Django imports.
    """
    # Add backend directory to Python path
    backend_dir = Path(__file__).resolve().parent.parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    # Set Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.development")

    import django

    django.setup()


async def verify_django_session(sessionid: Optional[str] = Cookie(None)) -> int:
    """
    Validate Django session cookie and return user_id.

    This allows FastAPI agents to share authentication with Django.
    The session cookie is set by Django on login and validated here.

    Args:
        sessionid: Django session cookie value

    Returns:
        User ID from the session

    Raises:
        HTTPException: If session is invalid or user not authenticated
    """
    if not sessionid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session cookie provided",
        )

    # Import Django components after setup
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.auth import get_user_model

    User = get_user_model()

    # Load session from database
    session = SessionStore(session_key=sessionid)

    # Check if session exists and is valid
    if not session.exists(sessionid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    # Get user ID from session
    user_id = session.get("_auth_user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated",
        )

    # Verify user exists and is active
    try:
        user = await User.objects.aget(pk=int(user_id), is_active=True)
        return user.pk
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )


async def get_notebook_config(notebook_id: int, user_id: int):
    """
    Load notebook with access validation.

    Args:
        notebook_id: Notebook primary key
        user_id: Authenticated user ID

    Returns:
        Notebook instance

    Raises:
        HTTPException: If notebook not found or access denied
    """
    from notebooks.models import Notebook

    try:
        notebook = await Notebook.objects.select_related("user").aget(
            id=notebook_id,
            user_id=user_id,
        )
        return notebook
    except Notebook.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found or access denied",
        )
