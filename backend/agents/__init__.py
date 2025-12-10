"""
Agents package for various AI-powered services.

This package provides modular AI agents for research and report generation:

- deep_researcher: Performs iterative web research with multi-agent coordination
- report_writer: Generates polished reports from research findings
- coordinator: Orchestrates multi-agent workflows with clarification support
"""

# Main public interfaces
from .coordinator import execute_task, TaskResult, TaskOptions
from .deep_researcher import run_research, ResearchResult
from .report_writer import run_writer, WriterResult

__all__ = [
    # Coordinator
    "execute_task",
    "TaskResult", 
    "TaskOptions",
    # Deep Researcher
    "run_research",
    "ResearchResult",
    # Report Writer
    "run_writer",
    "WriterResult",
]
