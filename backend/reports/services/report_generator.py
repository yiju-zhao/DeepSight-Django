"""
DeepReportGenerator adapter under services to remove factory indirection.
"""

import shutil
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .config import (
    get_model_provider_config,
    get_retriever_config,
    get_supported_providers,
    get_supported_retrievers,
    get_free_retrievers,
    get_time_range_mapping,
    get_search_depth_options,
    get_secrets_path,
)

logger = logging.getLogger(__name__)


class DeepReportGeneratorAdapter:
    """Adapter for DeepReportGenerator to implement our expected API"""

    def __init__(self, secrets_path: Optional[str] = None):
        self._generator = None
        self.secrets_path = secrets_path or get_secrets_path()
        self._temp_dirs = []

    @property
    def generator(self):
        if self._generator is None:
            try:
                from agents.report_agent.deep_report_generator import DeepReportGenerator
                # Use secrets_path if available, otherwise rely on environment variables
                # This allows the system to work without secrets.toml by using Django settings/.env
                if self.secrets_path:
                    self._generator = DeepReportGenerator(secrets_path=self.secrets_path)
                else:
                    # Initialize with default path, which will fall back to environment variables
                    # if the file doesn't exist (as per the refactoring plan)
                    self._generator = DeepReportGenerator(secrets_path="secrets.toml")
            except ImportError as e:
                raise ImportError(f"Failed to import DeepReportGenerator: {e}")
            except Exception as e:
                raise Exception(f"Failed to initialize DeepReportGenerator: {e}")
        return self._generator

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        try:
            logger.info(f"Validating report configuration: {config}")

            topic = config.get("topic", "").strip()
            selected_files_paths = config.get("selected_files_paths", [])
            article_title = config.get("article_title", "").strip()
            output_dir = config.get("output_dir")

            if not topic and not selected_files_paths:
                logger.error("Must provide either topic or selected_files_paths")
                return False

            if not article_title:
                if topic:
                    article_title = topic
                    config["article_title"] = article_title
                    logger.info(f"Using topic as article_title: {article_title}")
                else:
                    article_title = "Research Report"
                    config["article_title"] = article_title
                    logger.info(f"Using default article_title: {article_title}")

            if not output_dir:
                logger.error(f"Missing or empty output_dir: {output_dir}")
                return False

            provider = config.get("model_provider", "openai")
            provider_config = get_model_provider_config(provider)
            logger.info(
                f"Model provider '{provider}' config: api_key={'***' if provider_config.get('api_key') else 'MISSING'}"
            )
            if not provider_config.get("api_key"):
                logger.error(f"Missing API key for model provider: {provider}")
                return False

            retriever = config.get("retriever", "tavily")
            retriever_config = get_retriever_config(retriever)
            logger.info(
                f"Retriever '{retriever}' config: api_key={'***' if retriever_config.get('api_key') else 'MISSING'}"
            )
            requires_api_key = retriever not in get_free_retrievers()
            if requires_api_key and not retriever_config.get("api_key"):
                logger.error(f"Missing API key for retriever: {retriever}")
                return False

            logger.info("Report configuration validation passed")
            return True
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            return False

    def generate_report(self, config: Dict[str, Any]) -> Dict[str, Any]:
        try:
            deep_config = self._create_deep_config(config)
            result = self.generator.generate_report(deep_config)
            if not result.success:
                return {
                    "success": False,
                    "error_message": result.error_message or "Report generation failed",
                }
            generated_files = result.generated_files or []
            return {
                "success": True,
                "article_title": result.article_title,
                "generated_topic": getattr(result, "generated_topic", None),
                "report_content": getattr(result, "report_content", ""),
                "generated_files": generated_files,
                "processing_logs": result.processing_logs or [],
                "error_message": None,
            }
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {"success": False, "error_message": f"Report generation failed: {str(e)}"}

    def get_supported_providers(self) -> Dict[str, Any]:
        return {
            "model_providers": get_supported_providers(),
            "retrievers": get_supported_retrievers(),
            "free_retrievers": get_free_retrievers(),
            "time_ranges": list(get_time_range_mapping().keys()),
            "search_depths": get_search_depth_options(),
        }

    def cancel_generation(self, job_id: str) -> bool:
        try:
            self._cleanup_all_temp_directories()
            logger.info(f"Cleaned up temp directories for cancelled job {job_id}")
            return True
        except Exception as e:
            logger.error(
                f"Error during cancellation cleanup for job {job_id}: {e}"
            )
            return False

    @property
    def generator_name(self) -> str:
        return "report_agent"

    def _cleanup_temp_directory(self, temp_dir: str) -> None:
        try:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
                if temp_dir in self._temp_dirs:
                    self._temp_dirs.remove(temp_dir)
        except Exception as e:
            logger.warning(
                f"Failed to clean up temporary directory {temp_dir}: {e}"
            )

    def _cleanup_all_temp_directories(self) -> None:
        for temp_dir in self._temp_dirs.copy():
            self._cleanup_temp_directory(temp_dir)

    def _upload_to_minio(
        self, local_files: list, user_id: int, report_id: str, notebook_id: int = None
    ) -> list:
        from ..storage import StorageFactory

        minio_storage = StorageFactory.create_storage("minio")
        minio_files = minio_storage.store_generated_files(
            local_files, user_id, report_id, notebook_id
        )
        return minio_files

    def __del__(self):
        self._cleanup_all_temp_directories()

    def _create_deep_config(self, config: Dict[str, Any]) -> Any:
        try:
            import tempfile
            from agents.report_agent.deep_report_generator import (
                ReportGenerationConfig,
                ModelProvider,
                RetrieverType,
                TimeRange,
            )
            from agents.report_agent.prompts import PromptType

            model_provider_map = {
                "openai": ModelProvider.OPENAI,
                "google": ModelProvider.GOOGLE,
            }

            retriever_map = {
                "tavily": RetrieverType.TAVILY,
                "brave": RetrieverType.BRAVE,
                "serper": RetrieverType.SERPER,
                "you": RetrieverType.YOU,
                "bing": RetrieverType.BING,
                "duckduckgo": RetrieverType.DUCKDUCKGO,
                "searxng": RetrieverType.SEARXNG,
                "azure_ai_search": RetrieverType.AZURE_AI_SEARCH,
            }

            time_range_map = {
                "day": TimeRange.DAY,
                "week": TimeRange.WEEK,
                "month": TimeRange.MONTH,
                "year": TimeRange.YEAR,
            }

            prompt_type_map = {
                "general": PromptType.GENERAL,
                "financial": PromptType.FINANCIAL,
                "paper": PromptType.PAPER,
            }

            old_outline_path = None
            if config.get("old_outline") and config["old_outline"].strip():
                temp_outline_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix="_old_outline.txt", delete=False
                )
                temp_outline_file.write(config["old_outline"])
                temp_outline_file.close()
                old_outline_path = temp_outline_file.name

            deep_config = ReportGenerationConfig(
                topic=config.get("topic"),
                article_title=config.get("article_title")
                or f"Report_{config.get('report_id', 'Unknown')}",
                output_dir=str(config["output_dir"]),
                report_id=config.get("report_id"),
                model_provider=model_provider_map.get(
                    config.get("model_provider", "openai"), ModelProvider.OPENAI
                ),
                retriever=retriever_map.get(
                    config.get("retriever", "tavily"), RetrieverType.TAVILY
                ),
                temperature=config.get("temperature", 0.2),
                top_p=config.get("top_p", 0.4),
                prompt_type=prompt_type_map.get(
                    config.get("prompt_type", "general"), PromptType.GENERAL
                ),
                do_research=config.get("do_research", True),
                do_generate_outline=config.get("do_generate_outline", True),
                do_generate_article=config.get("do_generate_article", True),
                do_polish_article=config.get("do_polish_article", True),
                remove_duplicate=config.get("remove_duplicate", True),
                post_processing=config.get("post_processing", True),
                max_conv_turn=config.get("max_conv_turn", 3),
                max_perspective=config.get("max_perspective", 3),
                search_top_k=config.get("search_top_k", 10),
                initial_retrieval_k=config.get("initial_retrieval_k", 150),
                final_context_k=config.get("final_context_k", 20),
                reranker_threshold=config.get("reranker_threshold", 0.5),
                max_thread_num=config.get("max_thread_num", 10),
                time_range=time_range_map.get(config.get("time_range"))
                if config.get("time_range")
                else None,
                include_domains=config.get("include_domains", False),
                skip_rewrite_outline=config.get("skip_rewrite_outline", False),
                whitelist_domains=config.get("domain_list", [])
                if config.get("domain_list")
                else None,
                search_depth=config.get("search_depth", "basic"),
                old_outline_path=old_outline_path,
                selected_files_paths=config.get("selected_files_paths", []),
                user_id=config.get("user_id"),
                csv_session_code=config.get("csv_session_code", ""),
                csv_date_filter=config.get("csv_date_filter", ""),
            )

            if config.get("text_input"):
                deep_config.text_input = config["text_input"]
            if config.get("figure_data"):
                deep_config.figure_data = config["figure_data"]

            return deep_config
        except Exception as e:
            raise Exception(f"Failed to create DeepReportGenerator config: {e}")
