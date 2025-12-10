"""
Deep Researcher Module

This module provides a research agent that can perform iterative web searches
and synthesis to answer complex research questions, producing structured output
for downstream processing by the report_writer.
"""

from .interface import run_research
from .states import ResearchResult, SourceInfo

__all__ = ["run_research", "ResearchResult", "SourceInfo"]
