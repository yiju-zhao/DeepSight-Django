"""
Common utilities for CopilotKit agent servers.

Provides shared helper functions used across all agent implementations.
"""

import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configure logging for an agent service.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level
        
    Returns:
        Configured logger
    """
    log = logging.getLogger(name)
    log.setLevel(level)
    
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        log.addHandler(handler)
    
    return log


@lru_cache(maxsize=1)
def get_openai_api_key() -> str:
    """
    Get OpenAI API key from Django settings.
    
    Cached to avoid repeated settings access.
    
    Returns:
        OpenAI API key
    """
    from django.conf import settings
    return getattr(settings, "OPENAI_API_KEY", "")


@lru_cache(maxsize=1)
def get_mcp_server_url() -> str:
    """
    Get MCP server URL from Django settings.
    
    Returns:
        MCP server URL for RAGFlow integration
    """
    from django.conf import settings
    return getattr(settings, "RAGFLOW_MCP_URL", "http://localhost:9382/mcp/")


def format_agent_state(state: dict[str, Any]) -> dict[str, Any]:
    """
    Format agent state for CopilotKit AG-UI protocol.
    
    Ensures all required fields are present with defaults.
    
    Args:
        state: Raw agent state
        
    Returns:
        Formatted state with defaults
    """
    return {
        "current_step": state.get("current_step", "idle"),
        "iteration_count": state.get("iteration_count", 0),
        "graded_documents": state.get("graded_documents", []),
        "query_rewrites": state.get("query_rewrites", []),
        "synthesis_progress": state.get("synthesis_progress", 0),
        "total_tool_calls": state.get("total_tool_calls", 0),
        "agent_reasoning": state.get("agent_reasoning", ""),
    }
