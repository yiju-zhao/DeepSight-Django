"""
State Definitions for Report Writer Agent

This module defines the state objects and structured schemas used for
the report writer workflow.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class Section(BaseModel):
    """A section of the report."""
    title: str = Field(description="Section title")
    content: str = Field(description="Section content in markdown")
    level: int = Field(default=2, description="Heading level (1-4)")


class WriterResult(BaseModel):
    """
    Output contract from the writer agent.
    
    This is the final result of the writing process,
    containing the complete report and metadata.
    """
    final_report: str = Field(
        description="Complete report in markdown format"
    )
    sections: List[Section] = Field(
        default_factory=list,
        description="Parsed sections of the report"
    )
    word_count: int = Field(
        default=0,
        description="Total word count of the report"
    )
    language: str = Field(
        default="en",
        description="Language of the report (detected or specified)"
    )


class WriterInput(BaseModel):
    """
    Input contract for the writer agent.
    
    This matches the output of the deep_researcher module.
    """
    research_brief: str = Field(
        description="Original research question or topic"
    )
    findings: str = Field(
        description="Compressed research findings"
    )
    sources: List[dict] = Field(
        default_factory=list,
        description="List of source information dictionaries"
    )
    draft_outline: Optional[str] = Field(
        default=None,
        description="Optional outline to follow"
    )
    style: str = Field(
        default="academic",
        description="Writing style: 'academic', 'casual', 'technical', 'business'"
    )
