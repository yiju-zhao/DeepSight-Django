import os
import sys

if sys.platform == "darwin":  # macOS
    # Core macOS forking safety
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

    # PyTorch/OpenMP/MKL safety
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

    # Disable MPS completely due to Metal Performance Shaders kernel compilation issues
    os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
    os.environ.setdefault("PYTORCH_DISABLE_MPS", "1")

    # Library-specific safety
    os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import glob
import json
import logging
import pathlib
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum

import pandas as pd
from prompts import PromptType, configure_prompts, create_prompt_module

# Get the directory where the script is located
SCRIPT_DIR = pathlib.Path(__file__).parent.absolute()

# Add parent directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# NOTE: We perform knowledge_storm imports lazily (after prompt configuration)
# to ensure the correct prompt type is loaded before any modules evaluate
# their docstrings. See `_lazy_import_knowledge_storm()` below.

# Placeholder type hints (optional) – will be overwritten after lazy import
STORMWikiLMConfigs = None  # type: ignore
STORMWikiRunner = None  # type: ignore
STORMWikiRunnerArguments = None  # type: ignore
OpenAIModel = GoogleModel = None  # type: ignore
BraveRM = TavilySearchRM = SerperRM = YouRM = BingSearch = DuckDuckGoSearchRM = SearXNG = AzureAISearch = None  # type: ignore
get_whitelisted_domains = is_valid_source = None  # type: ignore
FileIOHelper = QueryLogger = load_api_key = truncate_filename = None  # type: ignore

# ---------------------------------------------------------------------------
# Lazy import helper
# ---------------------------------------------------------------------------

def _lazy_import_knowledge_storm():
    """Import knowledge_storm modules *after* prompts are configured.

    This avoids loading the default GENERAL prompts when the package-level
    imports evaluate docstrings at import time. We import once and cache the
    objects in ``globals()`` so subsequent calls are no-ops.
    """

    if globals().get("STORMWikiRunner") is not None:
        # Already imported
        return

    global STORMWikiLMConfigs, STORMWikiRunner, STORMWikiRunnerArguments
    global OpenAIModel, GoogleModel
    global BraveRM, TavilySearchRM, SerperRM, YouRM, BingSearch, DuckDuckGoSearchRM, SearXNG, AzureAISearch
    global get_whitelisted_domains, is_valid_source
    global FileIOHelper, QueryLogger, load_api_key, truncate_filename

    from knowledge_storm import (
        STORMWikiLMConfigs as _STORMWikiLMConfigs,
        STORMWikiRunner as _STORMWikiRunner,
        STORMWikiRunnerArguments as _STORMWikiRunnerArguments,
    )

    from knowledge_storm.lm import OpenAIModel as _OpenAIModel, GoogleModel as _GoogleModel

    from knowledge_storm.rm import (
        BraveRM as _BraveRM,
        TavilySearchRM as _TavilySearchRM,
        SerperRM as _SerperRM,
        YouRM as _YouRM,
        BingSearch as _BingSearch,
        DuckDuckGoSearchRM as _DuckDuckGoSearchRM,
        SearXNG as _SearXNG,
        AzureAISearch as _AzureAISearch,
    )

    from knowledge_storm.storm_wiki.modules.retriever import (
        get_whitelisted_domains as _get_whitelisted_domains,
        is_valid_source as _is_valid_source,
    )

    from knowledge_storm.utils import (
        FileIOHelper as _FileIOHelper,
        QueryLogger as _QueryLogger,
        load_api_key as _load_api_key,
        truncate_filename as _truncate_filename,
    )

    # Assign to globals so that other methods/classes can use them
    STORMWikiLMConfigs = _STORMWikiLMConfigs
    STORMWikiRunner = _STORMWikiRunner
    STORMWikiRunnerArguments = _STORMWikiRunnerArguments
    OpenAIModel = _OpenAIModel
    GoogleModel = _GoogleModel
    BraveRM = _BraveRM
    TavilySearchRM = _TavilySearchRM
    SerperRM = _SerperRM
    YouRM = _YouRM
    BingSearch = _BingSearch
    DuckDuckGoSearchRM = _DuckDuckGoSearchRM
    SearXNG = _SearXNG
    AzureAISearch = _AzureAISearch
    get_whitelisted_domains = _get_whitelisted_domains
    is_valid_source = _is_valid_source
    FileIOHelper = _FileIOHelper
    QueryLogger = _QueryLogger
    load_api_key = _load_api_key
    truncate_filename = _truncate_filename


class ModelProvider(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    XINFERENCE = "xinference"


class RetrieverType(str, Enum):
    TAVILY = "tavily"
    BRAVE = "brave"
    SERPER = "serper"
    YOU = "you"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    SEARXNG = "searxng"
    AZURE_AI_SEARCH = "azure_ai_search"


class TimeRange(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


@dataclass
class ReportGenerationConfig:
    """Configuration for report generation."""

    # Basic settings
    output_dir: str = "results/api"
    max_thread_num: int = 10
    model_provider: ModelProvider = ModelProvider.OPENAI
    model_uid: Optional[str] = None  # For Xinference: the model UID selected by user
    retriever: RetrieverType = RetrieverType.TAVILY
    temperature: float = 0.2
    top_p: float = 0.4
    prompt_type: PromptType = PromptType.GENERAL
    report_id: Optional[int] = None

    # Generation flags
    do_research: bool = True
    do_generate_outline: bool = True
    do_generate_article: bool = True
    do_polish_article: bool = True
    remove_duplicate: bool = True
    post_processing: bool = True

    # Search and generation parameters
    max_conv_turn: int = 3
    max_perspective: int = 3
    search_top_k: int = 10
    initial_retrieval_k: int = 150
    final_context_k: int = 20
    reranker_threshold: float = 0.5

    # Optional parameters
    time_range: Optional[TimeRange] = None
    include_domains: bool = False
    whitelist_domains: Optional[List[str]] = None
    search_depth: str = "basic"  # "basic" or "advanced" for TavilySearchRM
    old_outline_path: Optional[str] = None
    skip_rewrite_outline: bool = False

    # Content inputs
    topic: Optional[str] = None
    article_title: str = "StormReport"
    # Consolidated text input (replaces paper_path, transcript_path, paper_content, transcript_content)
    text_input: Optional[str] = None
    csv_path: Optional[str] = None
    author_json: Optional[str] = None
    caption_files: Optional[List[str]] = None
    selected_files_paths: Optional[List[str]] = None  # For image path fixing
    user_id: Optional[str] = None  # User ID for MinIO access

    # CSV processing options (for non-interactive API use)
    csv_session_code: Optional[str] = None
    csv_date_filter: Optional[str] = None  # Format: YYYY-MM-DD


@dataclass
class ReportGenerationResult:
    """Result of report generation."""

    success: bool
    article_title: str
    output_directory: str
    generated_files: List[str]
    error_message: Optional[str] = None
    processing_logs: List[str] = None
    report_content: Optional[str] = None
    generated_topic: Optional[str] = None


class DeepReportGenerator:
    """Class-based report generator optimized for API usage."""

    def __init__(self):
        """Initialize the report generator."""
        self.logger = logging.getLogger(__name__)
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )



    def generate_report(self, config: ReportGenerationConfig) -> ReportGenerationResult:
        """Generate a research report based on the provided configuration.

        Args:
            config: Configuration object containing all generation parameters

        Returns:
            ReportGenerationResult with success status and generated files
        """
        processing_logs = []

        try:
            # Import modular components
            from .config import ConfigurationManager
            from .io_operations import IOManager
            from .runner_orchestrator import RunnerOrchestrator

            # Initialize managers
            config_manager = ConfigurationManager()
            io_manager = IOManager()
            orchestrator = RunnerOrchestrator()

            # Store report_id for use in filename generation
            self.report_id = config.report_id

            # Configure prompts and perform lazy import
            configure_prompts(config.prompt_type)
            processing_logs.append(f"Prompts configured for {config.prompt_type.value} type")
            _lazy_import_knowledge_storm()

            # Load API keys
            config_manager.load_api_keys()
            processing_logs.append("API keys loaded successfully")

            # Validate inputs
            if (not config.topic and not config.text_input and
                not config.csv_path and not config.caption_files):
                raise ValueError(
                    "Either a topic, text input, CSV file, or caption files must be provided."
                )

            # Setup language models and configurations
            lm_configs = config_manager.setup_language_models(config)
            processing_logs.append(f"Language models configured for {config.model_provider}")

            # Create engine arguments
            engine_args = orchestrator.create_engine_arguments(config)

            # Setup retriever
            rm = config_manager.setup_retriever(config, engine_args)
            processing_logs.append(f"Retriever configured: {config.retriever}")

            # Process CSV metadata
            article_title, speakers, csv_text_input = io_manager.process_csv_metadata(config)
            processing_logs.append("CSV metadata processed")

            # Setup output directory
            article_output_dir = io_manager.setup_output_directory(config, article_title)

            # Initialize and configure runner
            runner = orchestrator.initialize_runner(engine_args, lm_configs, rm, config)

            # Configure runner content
            content_logs = orchestrator.configure_runner_content(
                runner, config, article_title, speakers, csv_text_input, article_output_dir
            )
            processing_logs.extend(content_logs)

            # Validate runner content
            orchestrator.validate_runner_content(config, runner)

            # Set article directory name
            folder_name = truncate_filename(article_title.replace(" ", "_").replace("/", "_"))
            runner.article_dir_name = folder_name

            # Log processing information
            orchestrator.log_processing_information(config, runner)

            # Execute the pipeline
            pipeline_logs = orchestrator.execute_pipeline(runner, config)
            processing_logs.extend(pipeline_logs)

            # Collect generated files
            generated_files = io_manager.collect_generated_files(article_output_dir)

            # Process final report content
            final_report_content = io_manager.process_final_report_content(config, article_output_dir)
            if final_report_content:
                processing_logs.append("Final report content processed")
            else:
                processing_logs.append("Post-processing disabled or no content to process")

            # Create report file if needed
            report_file_path = io_manager.create_report_file(config, article_output_dir, final_report_content)
            if report_file_path:
                generated_files.append(report_file_path)

            # Extract final metadata
            metadata = orchestrator.extract_final_metadata(runner, article_title)

            return ReportGenerationResult(
                success=True,
                article_title=metadata['final_article_title'],
                output_directory=article_output_dir,
                generated_files=generated_files,
                processing_logs=processing_logs,
                report_content=final_report_content,
                generated_topic=metadata['generated_topic'],
            )

        except Exception as e:
            error_message = f"Report generation failed: {str(e)}"
            self.logger.exception(error_message)
            return ReportGenerationResult(
                success=False,
                article_title=config.article_title,
                output_directory="",
                generated_files=[],
                error_message=error_message,
                processing_logs=processing_logs,
                generated_topic=None,
            )


# Convenience function for backward compatibility and simple usage
def generate_report_from_config(
    config: ReportGenerationConfig
) -> ReportGenerationResult:
    """Generate a report using the provided configuration.

    Args:
        config: Report generation configuration

    Returns:
        ReportGenerationResult with generation status and files
    """
    generator = DeepReportGenerator()
    return generator.generate_report(config)


if __name__ == "__main__":
    # Example usage for general technical reports
    general_config = ReportGenerationConfig(
        topic="Artificial Intelligence in Healthcare",
        output_dir="results/api_test",
        model_provider=ModelProvider.OPENAI,
        retriever=RetrieverType.TAVILY,
        prompt_type=PromptType.GENERAL,  # Use general prompts
        do_research=True,
        do_generate_outline=True,
        do_generate_article=True,
        do_polish_article=True,
    )

    # Example usage for financial analysis reports
    financial_config = ReportGenerationConfig(
        topic="Artificial Intelligence in Healthcare",
        output_dir="results/financial_test",
        model_provider=ModelProvider.OPENAI,
        retriever=RetrieverType.TAVILY,
        prompt_type=PromptType.FINANCIAL,  # Use financial prompts
        do_research=True,
        do_generate_outline=True,
        do_generate_article=True,
        do_polish_article=True,
    )

    # Example usage with Xinference
    # Note: model_uid must be provided when using Xinference
    # You can get available model UIDs from the running Xinference server
    xinference_config = ReportGenerationConfig(
        topic="Artificial Intelligence in Healthcare",
        output_dir="results/xinference_test",
        model_provider=ModelProvider.XINFERENCE,
        model_uid="qwen2.5-72b-instruct",  # Replace with your model UID
        retriever=RetrieverType.TAVILY,
        prompt_type=PromptType.GENERAL,
        do_research=True,
        do_generate_outline=True,
        do_generate_article=True,
        do_polish_article=True,
    )

    # Choose which config to use
    config = general_config  # Change to financial_config or xinference_config as needed

    result = generate_report_from_config(config)
    if result.success:
        print(f"Report generated successfully: {result.article_title}")
        print(f"Output directory: {result.output_directory}")
        print(f"Generated files: {result.generated_files}")
    else:
        print(f"Report generation failed: {result.error_message}")
