"""
Report Writer Module

This module provides a writer agent that generates polished reports
from research findings produced by the deep_researcher module.
"""

from .interface import run_writer
from .states import WriterResult

__all__ = ["run_writer", "WriterResult"]
