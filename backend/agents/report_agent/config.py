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

    def __init__(self, secrets_path: str = "secrets.toml"):
        self.secrets_path = secrets_path
        self.logger = logging.getLogger(__name__)

    def load_api_keys(self):
        """Load API keys from secrets.toml file."""
        _ensure_storm_imported()

        if load_api_key is None:
            self.logger.error("load_api_key function is not available after import")
            raise RuntimeError("Failed to import load_api_key function from knowledge_storm")

        try:
            load_api_key(toml_file_path=self.secrets_path)
        except Exception as e:
            self.logger.error(f"Failed to load API keys: {e}")
            raise

    def setup_language_models(self, config) -> 'STORMWikiLMConfigs':
        """Setup language model configurations based on provider."""
        _ensure_storm_imported()
        lm_configs = STORMWikiLMConfigs()

        if config.model_provider.value == "google":
            return self._setup_google_models(config, lm_configs)
        elif config.model_provider.value == "openai":
            return self._setup_openai_models(config, lm_configs)
        else:
            raise ValueError(f"Unsupported model provider: {config.model_provider}")

    def _setup_openai_models(self, config, lm_configs) -> 'STORMWikiLMConfigs':
        """Setup OpenAI language models."""
        openai_kwargs = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": config.temperature,
            "top_p": config.top_p,
        }

        # Setup different model configurations
        lm_configs.init_openai_model(
            api_key=openai_kwargs["api_key"],
            openai_type="openai",
            temperature=openai_kwargs["temperature"],
            top_p=openai_kwargs["top_p"],
        )

        return lm_configs

    def _setup_google_models(self, config, lm_configs) -> 'STORMWikiLMConfigs':
        """Setup Google language models."""
        google_kwargs = {
            "api_key": os.getenv("GOOGLE_API_KEY"),
            "temperature": config.temperature,
            "top_p": config.top_p,
        }

        lm_configs.set_conv_simulator_lm(GoogleModel(model=config.conv_simulator_lm, **google_kwargs))
        lm_configs.set_question_asker_lm(GoogleModel(model=config.question_asker_lm, **google_kwargs))
        lm_configs.set_outline_gen_lm(GoogleModel(model=config.outline_gen_lm, **google_kwargs))
        lm_configs.set_article_gen_lm(GoogleModel(model=config.article_gen_lm, **google_kwargs))
        lm_configs.set_article_polish_lm(GoogleModel(model=config.article_polish_lm, **google_kwargs))

        return lm_configs

    def setup_retriever(self, config, engine_args):
        """Setup retriever based on configuration."""
        _ensure_storm_imported()

        if config.retriever.value == "brave":
            return BraveRM(
                brave_search_api_key=os.getenv("BRAVE_API_KEY"),
                k=config.search_top_k,
            )
        elif config.retriever.value == "tavily":
            return TavilySearchRM(
                tavily_search_api_key=os.getenv("TAVILY_API_KEY"),
                k=config.search_top_k,
                include_raw_content=True,
            )
        elif config.retriever.value == "serper":
            return SerperRM(
                serper_search_api_key=os.getenv("SERPER_API_KEY"),
                query_params={"engine": "google", "location": "", "num": config.search_top_k},
            )
        elif config.retriever.value == "you":
            return YouRM(you_search_api_key=os.getenv("YOU_API_KEY"), k=config.search_top_k)
        elif config.retriever.value == "bing":
            return BingSearch(
                bing_search_api_key=os.getenv("BING_API_KEY"),
                k=config.search_top_k,
            )
        elif config.retriever.value == "duckduckgo":
            return DuckDuckGoSearchRM(k=config.search_top_k)
        elif config.retriever.value == "searxng":
            return SearXNG(
                searx_url=os.getenv("SEARXNG_URL", "http://localhost:8080"),
                k=config.search_top_k,
            )
        elif config.retriever.value == "azureaisearch":
            return AzureAISearch(
                azure_ai_search_api_key=os.getenv("AZURE_AI_SEARCH_API_KEY"),
                azure_ai_search_endpoint=os.getenv("AZURE_AI_SEARCH_ENDPOINT"),
                azure_ai_search_index=os.getenv("AZURE_AI_SEARCH_INDEX"),
                k=config.search_top_k,
            )
        else:
            raise ValueError(f"Unsupported retriever: {config.retriever}")