"""
Runner orchestration module for STORM report generation.

This module handles the main execution logic and coordinates
the STORM pipeline execution.
"""

import logging

# Preserve lazy import pattern
STORMWikiRunner = STORMWikiRunnerArguments = QueryLogger = None


def _ensure_storm_imported():
    """Ensure STORM modules are imported (delegated to main module)."""
    from . import deep_report_generator as drg

    drg._lazy_import_knowledge_storm()

    global STORMWikiRunner, STORMWikiRunnerArguments, QueryLogger
    STORMWikiRunner = drg.STORMWikiRunner
    STORMWikiRunnerArguments = drg.STORMWikiRunnerArguments
    QueryLogger = drg.QueryLogger


class RunnerOrchestrator:
    """Orchestrates the STORM runner execution."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_engine_arguments(self, config) -> "STORMWikiRunnerArguments":
        """Create and return STORM engine arguments."""
        _ensure_storm_imported()

        if STORMWikiRunnerArguments is None:
            self.logger.error("STORMWikiRunnerArguments is not available after import")
            raise RuntimeError(
                "Failed to import STORMWikiRunnerArguments from knowledge_storm"
            )

        return STORMWikiRunnerArguments(
            output_dir=config.output_dir,
            article_title=config.article_title,
            max_conv_turn=config.max_conv_turn,
            max_perspective=config.max_perspective,
            search_top_k=config.search_top_k,
            initial_retrieval_k=config.initial_retrieval_k,
            final_context_k=config.final_context_k,
            max_thread_num=config.max_thread_num,
            recent_content_only=config.time_range is not None,
            reranker_threshold=config.reranker_threshold,
            time_range=config.time_range.value if config.time_range else None,
            text_input=config.text_input,
            report_id=config.report_id,
        )

    def initialize_runner(
        self, engine_args, lm_configs, rm, config
    ) -> "STORMWikiRunner":
        """Initialize and configure the STORM runner."""
        _ensure_storm_imported()

        if STORMWikiRunner is None:
            self.logger.error("STORMWikiRunner is not available after import")
            raise RuntimeError("Failed to import STORMWikiRunner from knowledge_storm")

        runner = STORMWikiRunner(engine_args, lm_configs, rm)
        runner.author_json = config.author_json

        # Pass source_ids and user_id for image path fixing
        if config.source_ids:
            runner.source_ids = config.source_ids
        if config.user_id:
            runner.user_id = config.user_id

        return runner

    def configure_runner_content(
        self,
        runner,
        config,
        article_title: str,
        speakers: str | None,
        csv_text_input: str | None,
        output_dir: str,
    ) -> list[str]:
        """Configure runner with content and metadata."""
        processing_logs = []

        # Configure text input
        if config.text_input:
            runner.text_input = config.text_input
            processing_logs.append("Text input loaded")
        elif csv_text_input:
            runner.text_input = csv_text_input
            processing_logs.append("CSV text input loaded as text input")

        # Set additional metadata
        runner.speakers = speakers
        runner.article_title = article_title

        # Set up query logger
        runner.storm_article_generation.query_logger = QueryLogger(output_dir)

        # Handle figure data if provided
        if hasattr(config, "figure_data") and config.figure_data:
            runner.figure_data = config.figure_data
            processing_logs.append(
                f"Figure data loaded: {len(config.figure_data)} figures"
            )

        return processing_logs

    def validate_runner_content(self, config, runner) -> None:
        """Validate that runner has sufficient content to proceed."""
        if not config.topic and not runner.text_input:
            raise ValueError(
                "Either a topic or text input must be provided for report generation."
            )

    def log_processing_information(self, config, runner) -> None:
        """Log information about the processing configuration."""
        if config.topic:
            if runner.text_input:
                self.logger.info(
                    f"Topic and text input provided. The topic ('{config.topic}') "
                    f"will be improved using the text input."
                )
            else:
                self.logger.info(
                    f"Only topic ('{config.topic}') provided. "
                    f"Using the provided topic for improvement/guidance."
                )
        else:
            self.logger.info(
                "Text input provided (no topic). Key technology or innovations "
                "will be extracted from the text input to form a topic."
            )

    def execute_pipeline(self, runner, config) -> list[str]:
        """Execute the STORM pipeline."""
        processing_logs = []

        try:
            # Enhance topic with custom requirements if provided
            enhanced_topic = config.topic
            if config.parsed_requirements:
                try:
                    from .prompt_enhancer import PromptEnhancer

                    enhanced_topic = PromptEnhancer.enhance_topic_for_outline(
                        base_topic=config.topic or "",
                        parsed_requirements=config.parsed_requirements,
                    )

                    req_summary = PromptEnhancer.get_summary(config.parsed_requirements)
                    self.logger.info(
                        f"Enhanced topic with custom requirements: {req_summary}"
                    )
                    processing_logs.append(
                        f"Custom requirements applied: {req_summary}"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to enhance topic with requirements: {e}"
                    )
                    # Continue with original topic if enhancement fails
                    enhanced_topic = config.topic

            # Execute the pipeline
            runner.run(
                user_input=enhanced_topic,
                do_research=config.do_research,
                do_generate_outline=config.do_generate_outline,
                do_generate_article=config.do_generate_article,
                do_polish_article=config.do_polish_article,
                remove_duplicate=config.remove_duplicate,
                old_outline_path=config.old_outline_path,
                skip_rewrite_outline=config.skip_rewrite_outline,
            )

            runner.is_polishing_complete = True
            runner.post_run()
            runner.summary()
            processing_logs.append("Report generation completed")

            return processing_logs

        except Exception as e:
            self.logger.error(f"Error during pipeline execution: {e}")
            raise

    def extract_final_metadata(self, runner, article_title: str) -> dict:
        """Extract final metadata from the runner."""
        return {
            "final_article_title": getattr(runner, "generated_article_title", None)
            or article_title,
            "generated_topic": getattr(runner, "generated_topic", None),
        }
