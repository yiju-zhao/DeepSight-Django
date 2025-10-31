"""
Pytest configuration for RAGFlow tests.

This file configures Django settings for pytest so tests can run
without a full Django environment.
"""

import os
import sys
from pathlib import Path

import django
from django.conf import settings


# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))


def pytest_configure(config):
    """
    Configure Django settings before running tests.

    This allows tests to run without a full Django setup.
    """
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
            ],
            SECRET_KEY="test-secret-key-for-ragflow-tests",
            # RAGFlow settings
            RAGFLOW_BASE_URL="http://localhost:9380",
            RAGFLOW_API_KEY="test-api-key",
            RAGFLOW_LOGIN_TOKEN="test-login-token",
            # Disable migrations for tests
            MIGRATION_MODULES={},
        )
        django.setup()
