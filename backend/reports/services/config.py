"""
Settings-backed configuration helpers for the reports services.
Replaces the old reports/config/* modules.
"""

import os
from typing import Any, Dict, List, Optional

try:
    from django.conf import settings
except Exception:  # pragma: no cover - allow import without Django
    settings = None  # type: ignore


def _get_setting(key: str, default: Any = None) -> Any:
    # Prefer Django settings if available
    if settings and hasattr(settings, key):
        return getattr(settings, key)
    # Fallback to environment variables
    return os.getenv(key, default)


def get_secrets_path() -> Optional[str]:
    return _get_setting("REPORT_SECRETS_PATH", None)


def get_model_provider_config(provider: str) -> Dict[str, Any]:
    if provider == "openai":
        return {
            "api_key": _get_setting("OPENAI_API_KEY"),
            "organization": _get_setting("OPENAI_ORG"),
            "model": _get_setting("OPENAI_REPORT_MODEL", "gpt-4o-mini"),
            "temperature": 0.7,
            "max_tokens": 4000,
        }
    if provider == "google":
        return {
            "api_key": _get_setting("GOOGLE_API_KEY"),
            "model": _get_setting("GOOGLE_REPORT_MODEL", "gemini-pro"),
            "temperature": 0.7,
            "max_tokens": 4000,
        }
    return {}


def get_retriever_config(retriever: str) -> Dict[str, Any]:
    configs = {
        "tavily": {
            "api_key": _get_setting("TAVILY_API_KEY"),
            "search_depth": "advanced",
            "max_results": 10,
        },
        "brave": {"api_key": _get_setting("BRAVE_API_KEY"), "max_results": 10},
        "serper": {"api_key": _get_setting("SERPER_API_KEY"), "max_results": 10},
        "you": {"api_key": _get_setting("YOU_API_KEY"), "max_results": 10},
        "bing": {"api_key": _get_setting("BING_API_KEY"), "max_results": 10},
        "duckduckgo": {"max_results": 10, "timeout": 30},
        "searxng": {
            "base_url": _get_setting("SEARXNG_BASE_URL", "http://localhost:8080"),
            "max_results": 10,
        },
        "azure_ai_search": {
            "api_key": _get_setting("AZURE_AI_SEARCH_API_KEY"),
            "service_name": _get_setting("AZURE_AI_SEARCH_SERVICE_NAME"),
            "index_name": _get_setting("AZURE_AI_SEARCH_INDEX_NAME"),
        },
    }
    return configs.get(retriever, {})


def get_supported_providers() -> List[str]:
    return ["openai", "google"]


def get_supported_retrievers() -> List[str]:
    return [
        "tavily",
        "brave",
        "serper",
        "you",
        "bing",
        "duckduckgo",
        "searxng",
        "azure_ai_search",
    ]


def get_free_retrievers() -> List[str]:
    return ["duckduckgo", "searxng"]


def get_time_range_mapping() -> Dict[str, Any]:
    return {"day": "day", "week": "week", "month": "month", "year": "year"}


def get_search_depth_options() -> List[str]:
    return ["basic", "advanced"]


def validate_config(config: Dict[str, Any]) -> Dict[str, bool]:
    results: Dict[str, bool] = {}
    provider = config.get("model_provider", "openai")
    prov_cfg = get_model_provider_config(provider)
    results[f"{provider}_model"] = bool(prov_cfg.get("api_key"))

    retriever = config.get("retriever", "tavily")
    ret_cfg = get_retriever_config(retriever)
    requires_key = retriever not in get_free_retrievers()
    results[f"{retriever}_retriever"] = bool(ret_cfg.get("api_key") or not requires_key)
    results["secrets_file"] = bool(get_secrets_path())
    return results


class ReportSettingsConfig:
    """Minimal object to satisfy legacy signature in GenerationService."""

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, bool]:  # pragma: no cover
        return validate_config(config)

