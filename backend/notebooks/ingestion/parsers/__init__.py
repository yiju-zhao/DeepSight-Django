"""
Parsers for different file types.
"""

from .base_parser import BaseParser, ParseResult
from .docu_parser import DocuParser
from .media_parser import MediaParser
from .text_parser import TextParser
from .table_parser import TableParser

__all__ = [
    "BaseParser",
    "ParseResult",
    "DocuParser",
    "MediaParser",
    "TextParser",
    "TableParser",
]
