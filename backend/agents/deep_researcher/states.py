"""
State Definitions for Deep Researcher Agent

This module defines the state objects and structured schemas used for
the research agent workflow, including researcher state management,
output schemas, and data contracts for the coordinator.
"""

import operator
from typing import Sequence
from typing_extensions import TypedDict, Annotated

from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


# ============================================================================
# DATA CONTRACTS (Output schemas for coordinator consumption)
# ============================================================================

class SourceInfo(BaseModel):
    """Information about a research source."""
    url: str = Field(description="URL of the source")
    title: str = Field(description="Title of the source document")
    snippet: str = Field(description="Relevant excerpt from the source")
    relevance_score: float | None = Field(
        default=None, 
        description="Relevance score (0-1) if available"
    )


class ResearchResult(BaseModel):
    """
    Standard output contract from research agent.
    
    This is the data structure passed to the report_writer or
    returned to the coordinator.
    """
    findings: str = Field(
        description="Compressed research summary with key insights"
    )
    sources: list[SourceInfo] = Field(
        default_factory=list,
        description="List of cited sources with URLs and snippets"
    )
    raw_notes: list[str] = Field(
        default_factory=list,
        description="Unprocessed research notes for audit/reference"
    )
    research_brief: str | None = Field(
        default=None,
        description="Original research query/brief"
    )


# ============================================================================
# INTERNAL STATE DEFINITIONS (LangGraph workflow states)
# ============================================================================

class ResearcherState(TypedDict):
    """
    State for individual research worker containing message history 
    and research metadata.

    This state tracks the researcher's conversation, iteration count for limiting
    tool calls, the research topic being investigated, compressed findings,
    and raw research notes for detailed analysis.
    """
    # Messages exchanged during research
    researcher_messages: Annotated[Sequence[BaseMessage], add_messages]
    # Counter for tool call iterations to prevent infinite loops
    tool_call_iterations: int
    # The specific topic this worker is researching
    research_topic: str
    # Compressed summary of research findings
    compressed_research: str
    # Raw unprocessed notes from research
    raw_notes: Annotated[list[str], operator.add]


class ResearcherOutputState(TypedDict):
    """
    Output state for the research worker containing final research results.

    This represents the final output of an individual research worker,
    with compressed findings and all raw notes.
    """
    compressed_research: str
    raw_notes: Annotated[list[str], operator.add]
    researcher_messages: Annotated[Sequence[BaseMessage], add_messages]


class SupervisorState(TypedDict):
    """
    State for the multi-agent research supervisor.

    Manages coordination between supervisor and research workers, tracking
    research progress and accumulating findings from multiple sub-agents.
    """
    # Messages exchanged with supervisor for coordination
    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages]
    # Detailed research brief that guides the overall research direction
    research_brief: str
    # Processed and structured notes ready for final compilation
    notes: Annotated[list[str], operator.add]
    # Counter tracking the number of research iterations performed
    research_iterations: int
    # Raw unprocessed research notes collected from sub-agent research
    raw_notes: Annotated[list[str], operator.add]


# ============================================================================
# STRUCTURED OUTPUT SCHEMAS (For LLM structured output)
# ============================================================================

class ClarifyWithUser(BaseModel):
    """Schema for user clarification decisions during scoping phase."""
    need_clarification: bool = Field(
        description="Whether the user needs to be asked a clarifying question.",
    )
    question: str = Field(
        description="A question to ask the user to clarify the report scope",
    )
    verification: str = Field(
        description="Verification message that we will start research after clarification.",
    )


class ResearchQuestion(BaseModel):
    """Schema for research brief generation."""
    research_brief: str = Field(
        description="A research question that will be used to guide the research.",
    )


class Summary(BaseModel):
    """Schema for webpage content summarization."""
    summary: str = Field(description="Concise summary of the webpage content")
    key_excerpts: str = Field(description="Important quotes and excerpts from the content")
