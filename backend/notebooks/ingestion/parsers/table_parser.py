"""
Table parser for Excel files using pandas.
Converts Excel sheets to markdown tables.
"""

import logging
from typing import Any, Optional

from ..exceptions import ParseError
from .base_parser import BaseParser, ParseResult


class TableParser(BaseParser):
    """Parser for Excel files that converts data to markdown tables."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    async def parse(self, file_path: str, metadata: dict[str, Any]) -> ParseResult:
        """
        Parse Excel file and convert to markdown tables.

        Args:
            file_path: Path to Excel file
            metadata: File metadata (filename, extension, etc.)

        Returns:
            ParseResult with markdown table content and metadata
        """
        file_extension = metadata.get("file_extension", "").lower()

        if file_extension in [".xlsx", ".xls"]:
            return await self._parse_excel(file_path, metadata)
        else:
            raise ParseError(f"Unsupported table file extension: {file_extension}")

    async def _parse_excel(
        self, file_path: str, metadata: dict[str, Any]
    ) -> ParseResult:
        """Parse Excel spreadsheet and convert to markdown tables."""
        self.logger.info(f"Processing Excel file: {file_path}")

        try:
            import pandas as pd

            # Read all sheets from Excel file
            excel_file = pd.ExcelFile(file_path)

            content = ""
            total_rows = 0
            total_cols = 0
            sheet_count = len(excel_file.sheet_names)

            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)

                # Add sheet header
                content += f"\n## Sheet: {sheet_name}\n\n"

                # Convert dataframe to markdown table
                if not df.empty:
                    # Replace NaN with empty string for cleaner markdown
                    df = df.fillna('')

                    # Convert to markdown table format
                    markdown_table = df.to_markdown(index=False)
                    content += markdown_table + "\n\n"

                    total_rows += len(df)
                    total_cols = max(total_cols, len(df.columns))
                else:
                    content += "*Empty sheet*\n\n"

            excel_metadata = {
                "processing_method": "pandas_table_parser",
                "sheet_count": sheet_count,
                "total_rows": total_rows,
                "total_columns": total_cols,
                "word_count": len(content.split()),
                "file_type": "excel_spreadsheet",
            }

            return ParseResult(
                content=content,
                metadata=excel_metadata,
                features_available=[
                    "table_extraction",
                    "data_analysis",
                    "structured_data",
                    "markdown_tables",
                ],
            )

        except ImportError as e:
            self.logger.error(f"Required libraries not available: {e}")
            raise ParseError(
                f"Excel parsing requires pandas and tabulate libraries: {e}"
            ) from e
        except Exception as e:
            self.logger.error(f"Excel processing failed: {e}")
            raise ParseError(f"Excel processing failed: {e}") from e
