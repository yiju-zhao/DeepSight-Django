"""
Xinference client utilities for listing and managing models.
"""

import logging
from typing import List, Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


def get_available_xinference_models() -> List[Dict[str, str]]:
    """
    Get list of available LLM models from Xinference.

    Returns:
        List of dicts with 'uid', 'name', and 'display_name' keys
    """
    try:
        from xinference.client import Client

        api_base = getattr(settings, 'XINFERENCE_API_BASE', None)
        if not api_base:
            logger.warning("XINFERENCE_API_BASE not configured")
            return []

        # Extract host and port from api_base (remove /v1 suffix if present)
        base_url = api_base.replace('/v1', '')

        client = Client(base_url)

        # List all running models
        running_models = client.list_models()

        models = []
        for model_uid, model_info in running_models.items():
            # Extract model information
            model_name = model_info.get('model_name', model_uid)
            model_type = model_info.get('model_type', 'LLM')

            # Only include LLM models
            if model_type.lower() == 'llm':
                display_name = f"{model_name} - Xinference"
                models.append({
                    'uid': model_uid,
                    'name': model_name,
                    'display_name': display_name,
                    'provider': 'xinference'
                })

        return models

    except ImportError:
        logger.error("xinference package not installed")
        return []
    except Exception as e:
        logger.error(f"Error listing Xinference models: {e}")
        return []


def get_xinference_model_info(model_uid: str) -> Optional[Dict]:
    """
    Get information about a specific Xinference model.

    Args:
        model_uid: The UID of the model

    Returns:
        Dict with model information or None if not found
    """
    try:
        from xinference.client import Client

        api_base = getattr(settings, 'XINFERENCE_API_BASE', None)
        if not api_base:
            return None

        base_url = api_base.replace('/v1', '')
        client = Client(base_url)

        running_models = client.list_models()
        return running_models.get(model_uid)

    except Exception as e:
        logger.error(f"Error getting Xinference model info: {e}")
        return None
