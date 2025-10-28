"""
Base Django settings for DeepSight project.

These settings are common across all environments.
For production-specific settings, see production.py
For development-specific settings, see development.py
"""

import os
import warnings
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

# Suppress Pydantic serialization warnings from LiteLLM in Celery workers
warnings.filterwarnings("ignore", message=".*Pydantic serializer warnings.*")
warnings.filterwarnings("ignore", message=".*PydanticSerializationUnexpectedValue.*")
warnings.filterwarnings("ignore", message=".*Expected .* fields but got .*")
warnings.filterwarnings("ignore", message=".*serialized value may not be as expected.*")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def get_env_value(env_variable):
    """Get environment variable or raise exception"""
    try:
        return os.environ[env_variable]
    except KeyError:
        error_msg = f"Set the {env_variable} environment variable"
        raise ImproperlyConfigured(error_msg)


def get_env_bool(env_variable, default=False):
    """Get environment variable as boolean"""
    value = os.getenv(env_variable, str(default)).lower()
    return value in ("true", "1", "yes", "on")


# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key-change-in-production")

# ==============================================================================
# HOST CONFIGURATION
# ==============================================================================

HOST_IP = os.getenv("HOST_IP", "localhost")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
FRONTEND_PORT = os.getenv("FRONTEND_PORT", "5173")

# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "storages",
]

LOCAL_APPS = [
    # Core applications
    "core",
    "infrastructure",
    # Feature applications
    "users",
    "notebooks",
    "reports",
    "conferences",
    "podcast",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

# Custom user model
AUTH_USER_MODEL = "users.User"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ==============================================================================
# STATIC FILES
# ==============================================================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ==============================================================================
# DEFAULT FIELD TYPES
# ==============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================================================
# DJANGO REST FRAMEWORK
# ==============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

# ==============================================================================
# drf-spectacular (OpenAPI) configuration
# ==============================================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "DeepSight API",
    "DESCRIPTION": "DeepSight backend API with app-specific endpoints",
    "VERSION": "1.0.0",
    # Optional: enable schema optimizations
    "SERVE_INCLUDE_SCHEMA": False,
    # Optional: component splitting and enum naming
    # "COMPONENT_SPLIT_REQUEST": True,
}

# ==============================================================================
# CORS CONFIGURATION
# ==============================================================================

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    f"http://{HOST_IP}:{FRONTEND_PORT}",
    f"http://localhost:{FRONTEND_PORT}",
]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "cache-control",
]

# ==============================================================================
# STORAGE CONFIGURATION
# ==============================================================================

DEFAULT_STORAGE_BACKEND = "minio"
DEFAULT_FILE_STORAGE = "infrastructure.storage.backends.MinIOStorage"

# MinIO Configuration
MINIO_USE_SSL = get_env_bool("MINIO_SECURE", False)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_PUBLIC_ENDPOINT = os.getenv(
    "MINIO_PUBLIC_ENDPOINT", os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
)
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "deepsight-users")
MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")

# AWS S3 settings configured for MinIO compatibility (used by boto3/django-storages)
AWS_ACCESS_KEY_ID = MINIO_ACCESS_KEY
AWS_SECRET_ACCESS_KEY = MINIO_SECRET_KEY
AWS_STORAGE_BUCKET_NAME = MINIO_BUCKET_NAME
AWS_S3_ENDPOINT_URL = MINIO_ENDPOINT
AWS_S3_REGION_NAME = MINIO_REGION
AWS_S3_USE_SSL = MINIO_USE_SSL
AWS_S3_VERIFY = MINIO_USE_SSL

# ==============================================================================
# VECTOR DATABASE CONFIGURATION (MILVUS)
# ==============================================================================

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "user_vectors")

# ==============================================================================
# RAGFLOW CONFIGURATION
# ==============================================================================

RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY")
RAGFLOW_LOGIN_TOKEN = os.getenv("RAGFLOW_LOGIN_TOKEN")
RAGFLOW_BASE_URL = os.getenv("RAGFLOW_BASE_URL", "https://demo.ragflow.io:9380")
RAGFLOW_DEFAULT_CHUNK_METHOD = os.getenv("RAGFLOW_CHUNK_METHOD", "naive")
RAGFLOW_DEFAULT_EMBEDDING_MODEL = os.getenv(
    "RAGFLOW_EMBEDDING_MODEL", "Qwen3-Embedding-0.6B@Xinference"
)
RAGFLOW_CHAT_MODEL = os.getenv("RAGFLOW_CHAT_MODEL", "deepseek-chat@DeepSeek")

# ==============================================================================
# CELERY CONFIGURATION
# ==============================================================================

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# ==============================================================================
# AI SERVICE CONFIGURATION
# ==============================================================================

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORG = os.getenv("OPENAI_ORG")
OPENAI_PROJECT = os.getenv("OPENAI_PROJECT")

# Azure OpenAI Configuration
AZURE_API_KEY = os.getenv("AZURE_API_KEY")

# Google AI Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Xinference Configuration
XINFERENCE_API_BASE = os.getenv("XINFERENCE_API_BASE")
XINFERENCE_API_KEY = os.getenv("XINFERENCE_API_KEY", "dummy")

# ==============================================================================
# SEARCH API CONFIGURATION
# ==============================================================================

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
YOU_API_KEY = os.getenv("YOU_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")
SEARXNG_URL = os.getenv("SEARXNG_URL")
SEARXNG_API_KEY = os.getenv("SEARXNG_API_KEY")

# Azure AI Search Configuration
AZURE_AI_SEARCH_API_KEY = os.getenv("AZURE_AI_SEARCH_API_KEY")
AZURE_AI_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
AZURE_AI_SEARCH_INDEX = os.getenv("AZURE_AI_SEARCH_INDEX")

# ==============================================================================
# TTS CONFIGURATION
# ==============================================================================

# Higgs TTS (OpenAI-compatible) Configuration
HIGGS_API_BASE = os.getenv("HIGGS_API_BASE", "http://localhost:8000/v1")
HIGGS_TTS_MODEL = os.getenv("HIGGS_TTS_MODEL")

# ==============================================================================
# DOCUMENT PROCESSING
# ==============================================================================

MINERU_BASE_URL = os.getenv("MINERU_BASE_URL")

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
