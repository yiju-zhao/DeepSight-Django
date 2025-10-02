"""
Configuration module for STORM report generation.

This module handles all configuration-related operations including
model setup, retriever configuration, and environment setup.
"""

import os
import logging
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum
from django.conf import settings

# Preserve the existing lazy import pattern
STORMWikiLMConfigs = None
OpenAIModel = GoogleModel = None
BraveRM = TavilySearchRM = SerperRM = YouRM = BingSearch = DuckDuckGoSearchRM = SearXNG = AzureAISearch = None
load_api_key = None

def _ensure_storm_imported():
    """Ensure STORM modules are imported (delegated to main module)."""
    from . import deep_report_generator as drg
    drg._lazy_import_knowledge_storm()

    # Update globals from main module
    global STORMWikiLMConfigs, OpenAIModel, GoogleModel
    global BraveRM, TavilySearchRM, SerperRM, YouRM, BingSearch, DuckDuckGoSearchRM, SearXNG, AzureAISearch
    global load_api_key

    STORMWikiLMConfigs = drg.STORMWikiLMConfigs
    OpenAIModel = drg.OpenAIModel
    GoogleModel = drg.GoogleModel
    BraveRM = drg.BraveRM
    TavilySearchRM = drg.TavilySearchRM
    SerperRM = drg.SerperRM
    YouRM = drg.YouRM
    BingSearch = drg.BingSearch
    DuckDuckGoSearchRM = drg.DuckDuckGoSearchRM
    SearXNG = drg.SearXNG
    AzureAISearch = drg.AzureAISearch
    load_api_key = drg.load_api_key


class ConfigurationManager:
    """Manages configuration and setup for STORM report generation."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def load_api_keys(self):
        """Load API keys from Django settings.

        Note: This method is kept for backward compatibility but no longer
        loads from secrets.toml. All keys are now read from Django settings
        which loads from .env files.
        """
        self.logger.info("Using API keys from Django settings (.env file)")

    def setup_language_models(self, config) -> 'STORMWikiLMConfigs':
        """Setup language model configurations based on provider."""
        _ensure_storm_imported()
        lm_configs = STORMWikiLMConfigs()

        if config.model_provider.value == "google":
            return self._setup_google_models(config, lm_configs)
        elif config.model_provider.value == "openai":
            return self._setup_openai_models(config, lm_configs)
        elif config.model_provider.value == "xinference":
            return self._setup_xinference_models(config, lm_configs)
        else:
            raise ValueError(f"Unsupported model provider: {config.model_provider}")

    def _setup_openai_models(self, config, lm_configs) -> 'STORMWikiLMConfigs':
        """Setup OpenAI language models."""
        openai_api_key = settings.OPENAI_API_KEY
        azure_api_key = getattr(settings, 'AZURE_API_KEY', '')  # Optional fallback

        # Setup different model configurations
        lm_configs.init_openai_model(
            openai_api_key=openai_api_key,
            azure_api_key=azure_api_key,
            openai_type="openai",
            temperature=config.temperature,
            top_p=config.top_p,
        )

        # Set topic improver LM for OpenAI (needed for consistency)
        from .knowledge_storm.lm import LitellmModel
        openai_kwargs = {
            "api_key": openai_api_key,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "api_base": None,
        }
        lm_configs.set_topic_improver_lm(LitellmModel(
            model="gpt-4.1-mini", max_tokens=500, **openai_kwargs
        ))

        return lm_configs

    def _setup_xinference_models(self, config, lm_configs) -> 'STORMWikiLMConfigs':
        """Setup Xinference language models."""
        xinference_api_base = settings.XINFERENCE_API_BASE
        xinference_model = settings.XINFERENCE_MODEL
        xinference_api_key = getattr(settings, 'XINFERENCE_API_KEY', 'dummy')

        if not xinference_api_base or not xinference_model:
            raise ValueError("XINFERENCE_API_BASE and XINFERENCE_MODEL must be set")

        lm_configs.init_xinference_model(
            api_base=xinference_api_base,
            model=xinference_model,
            api_key=xinference_api_key,
            temperature=config.temperature,
            top_p=config.top_p,
        )

        return lm_configs

    def _setup_google_models(self, config, lm_configs) -> 'STORMWikiLMConfigs':
        """Setup Google language models using LitellmModel."""
        google_api_key = settings.GOOGLE_API_KEY

        # Setup Google model configurations using init_google_model method in engine
        lm_configs.init_google_model(
            google_api_key=google_api_key,
            temperature=config.temperature,
            top_p=config.top_p,
        )

        return lm_configs

    def setup_retriever(self, config, engine_args):
        """Setup retriever based on configuration."""
        _ensure_storm_imported()

        if config.retriever.value == "brave":
            return BraveRM(
                brave_search_api_key=getattr(settings, 'BRAVE_API_KEY', None),
                k=config.search_top_k,
            )
        elif config.retriever.value == "tavily":
            return TavilySearchRM(
                tavily_search_api_key=getattr(settings, 'TAVILY_API_KEY', None),
                k=config.search_top_k,
                include_raw_content=True,
            )
        elif config.retriever.value == "serper":
            return SerperRM(
                serper_search_api_key=getattr(settings, 'SERPER_API_KEY', None),
                query_params={"engine": "google", "location": "", "num": config.search_top_k},
            )
        elif config.retriever.value == "you":
            return YouRM(you_search_api_key=getattr(settings, 'YOU_API_KEY', None), k=config.search_top_k)
        elif config.retriever.value == "bing":
            return BingSearch(
                bing_search_api_key=getattr(settings, 'BING_API_KEY', None),
                k=config.search_top_k,
            )
        elif config.retriever.value == "duckduckgo":
            return DuckDuckGoSearchRM(k=config.search_top_k)
        elif config.retriever.value == "searxng":
            searxng_url = getattr(settings, 'SEARXNG_URL', 'http://localhost:8080')
            searxng_api_key = getattr(settings, 'SEARXNG_API_KEY', None)

            return SearXNG(
                searxng_api_url=searxng_url,
                searxng_api_key=searxng_api_key,
                k=config.search_top_k,
            )
        elif config.retriever.value == "azureaisearch":
            return AzureAISearch(
                azure_ai_search_api_key=getattr(settings, 'AZURE_AI_SEARCH_API_KEY', None),
                azure_ai_search_endpoint=getattr(settings, 'AZURE_AI_SEARCH_ENDPOINT', None),
                azure_ai_search_index=getattr(settings, 'AZURE_AI_SEARCH_INDEX', None),
                k=config.search_top_k,
            )
        else:
            raise ValueError(f"Unsupported retriever: {config.retriever}")