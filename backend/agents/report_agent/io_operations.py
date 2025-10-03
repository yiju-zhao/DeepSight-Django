"""
I/O operations module for STORM report generation.

This module handles all file I/O operations including content loading,
file processing, and output collection.
"""

import os
import glob
import tempfile
import logging
from typing import List, Optional, Union, Tuple
import pandas as pd
from pathlib import Path

# Preserve lazy import pattern
FileIOHelper = truncate_filename = None

def _ensure_storm_imported():
    """Ensure STORM modules are imported (delegated to main module)."""
    from . import deep_report_generator as drg
    drg._lazy_import_knowledge_storm()

    global FileIOHelper, truncate_filename
    FileIOHelper = drg.FileIOHelper
    truncate_filename = drg.truncate_filename


class IOManager:
    """Manages I/O operations for STORM report generation."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def load_content_from_file(self, file_path: str) -> Optional[str]:
        """Load content from a .txt or .md file and clean it."""
        if not os.path.exists(file_path):
            self.logger.warning(f"File not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read().strip()
                if not content:
                    self.logger.warning(f"File is empty: {file_path}")
                    return None

                # Clean and normalize content
                lines = content.split("\n")
                cleaned_lines = [line.strip() for line in lines if line.strip()]
                return "\n".join(cleaned_lines)
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None

    def load_structured_data(self, path: str) -> Union[str, List[str], None]:
        """Load structured data from a given path and clean paper content."""
        if os.path.isdir(path):
            all_content = []
            for file_path in glob.glob(os.path.join(path, "*.txt")) + glob.glob(
                os.path.join(path, "*.md")
            ):
                content = self.load_content_from_file(file_path)
                if content:
                    all_content.append(content)
            return all_content if all_content else None
        else:
            return self.load_content_from_file(path)

    def process_csv_metadata(self, config) -> Tuple[str, Optional[str], Optional[Union[str, List[str]]]]:
        """Process CSV metadata and return consolidated information."""
        _ensure_storm_imported()

        # Default values
        article_title = config.article_title
        speakers = None
        csv_text_input = None

        # Handle CSV metadata processing
        if config.csv_path and os.path.exists(config.csv_path):
            try:
                df = pd.read_csv(config.csv_path)

                # Process CSV content
                csv_text_input = self._process_csv_content(df, config)

                # Extract speakers if available
                if "speaker" in df.columns:
                    unique_speakers = df["speaker"].dropna().unique().tolist()
                    if unique_speakers:
                        speakers = ", ".join(unique_speakers)

                # Use CSV-derived title if available
                if hasattr(config, 'csv_derived_title') and config.csv_derived_title:
                    article_title = config.csv_derived_title

            except Exception as e:
                self.logger.error(f"Error processing CSV file {config.csv_path}: {e}")

        return article_title, speakers, csv_text_input

    def _process_csv_content(self, df: pd.DataFrame, config) -> Optional[str]:
        """Process CSV content based on configuration."""
        try:
            # Define date conversion function
            def convert_date_format(date_str):
                try:
                    dt_obj = pd.to_datetime(date_str).date()
                    return dt_obj.strftime("%B %d, %Y")
                except:
                    return str(date_str)

            # Apply various CSV processing logic based on config
            consolidated_content = []

            for _, row in df.iterrows():
                # Process each row based on available columns
                row_content = []

                if "content" in df.columns and pd.notna(row["content"]):
                    row_content.append(str(row["content"]))

                if "text" in df.columns and pd.notna(row["text"]):
                    row_content.append(str(row["text"]))

                if "description" in df.columns and pd.notna(row["description"]):
                    row_content.append(str(row["description"]))

                # Add speaker information if available
                if "speaker" in df.columns and pd.notna(row["speaker"]):
                    speaker_info = f"Speaker: {row['speaker']}"
                    row_content.insert(0, speaker_info)

                # Add date information if available
                if "date" in df.columns and pd.notna(row["date"]):
                    date_info = f"Date: {convert_date_format(row['date'])}"
                    row_content.insert(0, date_info)

                if row_content:
                    consolidated_content.append(" | ".join(row_content))

            return "\n\n".join(consolidated_content) if consolidated_content else None

        except Exception as e:
            self.logger.error(f"Error processing CSV content: {e}")
            return None

    def collect_generated_files(self, output_dir: str) -> List[str]:
        """Collect all generated files from the output directory."""
        generated_files = []

        try:
            # Collect all files from the output directory
            all_files = glob.glob(os.path.join(output_dir, "*"))

            # Filter to only include files (not directories) and common report file types
            for file_path in all_files:
                if (os.path.isfile(file_path) and
                    any(file_path.endswith(ext) for ext in
                        ['.md', '.txt', '.json', '.jsonl', '.html', '.pdf', '.csv'])):
                    generated_files.append(file_path)

            self.logger.info(
                f"Collected {len(generated_files)} files from output directory: "
                f"{[os.path.basename(f) for f in generated_files]}"
            )

            # Also collect the basic storm files specifically (for backwards compatibility)
            basic_storm_files = [
                os.path.join(output_dir, "storm_gen_outline.txt"),
                os.path.join(output_dir, "storm_gen_article.md"),
                os.path.join(output_dir, "storm_gen_article_polished.md"),
            ]

            # Add any basic files that weren't already collected
            for file_path in basic_storm_files:
                if file_path not in generated_files and os.path.exists(file_path):
                    generated_files.append(file_path)

            return [f for f in generated_files if os.path.exists(f)]

        except Exception as e:
            self.logger.error(f"Error collecting generated files: {e}")
            return []

    def setup_output_directory(self, config, article_title: str) -> str:
        """Setup and return the output directory path."""
        _ensure_storm_imported()

        if truncate_filename is None:
            self.logger.error("truncate_filename function is not available after import")
            raise RuntimeError("Failed to import truncate_filename function from knowledge_storm")

        # Set article directory name (but don't create subfolder - use output_dir directly)
        folder_name = truncate_filename(
            article_title.replace(" ", "_").replace("/", "_")
        )

        # Use output directory directly without creating subfolder
        article_output_dir = config.output_dir
        os.makedirs(article_output_dir, exist_ok=True)

        return article_output_dir

    def process_final_report_content(self, config, output_dir: str) -> Optional[str]:
        """Process and return the final report content."""
        if not config.post_processing:
            return None

        polished_article_path = os.path.join(output_dir, "storm_gen_article_polished.md")
        if not os.path.exists(polished_article_path):
            return None

        try:
            if config.source_ids:
                # Apply full post-processing with image path fixing
                with open(polished_article_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Apply other post-processing
                from agents.report_agent.utils.post_processing import (
                    remove_citations,
                    remove_captions,
                    remove_figure_placeholders,
                )

                content = remove_citations(content, True)
                content = remove_captions(content, True)
                content = remove_figure_placeholders(content, True)

                return content
            else:
                # No image path fixing needed, just apply traditional post-processing
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.md', delete=False) as temp_file:
                    from agents.report_agent.utils.post_processing import process_file
                    process_file(polished_article_path, temp_file.name, config.post_processing)

                    with open(temp_file.name, 'r', encoding='utf-8') as f:
                        content = f.read()

                    os.unlink(temp_file.name)
                    return content

        except Exception as e:
            self.logger.error(f"Error processing final report content: {e}")
            return None

    def create_report_file(self, config, output_dir: str, content: str) -> Optional[str]:
        """Create the final report file and return its path."""
        if not content or not config.report_id:
            return None

        report_file_path = os.path.join(output_dir, f"report_{config.report_id}.md")
        try:
            with open(report_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"Created report_{config.report_id}.md file")
            return report_file_path
        except Exception as e:
            self.logger.warning(f"Failed to create report_{config.report_id}.md file: {e}")
            return None