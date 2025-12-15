"""
Public Interface for Deep Researcher Agent

This module provides the public async API for the research agent,
suitable for use by the coordinator or direct API calls.
"""

import asyncio
import logging

from .states import ResearchResult
from .graph import execute_research
from .config import ResearchConfig


logger = logging.getLogger(__name__)


async def run_research(
    topic: str,
    max_depth: int = 3,
    max_iterations: int | None = None,
    timeout: float | None = None,
) -> ResearchResult:
    """
    Execute a deep research workflow on the given topic.
    
    This is the main public interface for the deep_researcher module.
    It returns a structured ResearchResult that can be passed to
    the report_writer for final report generation.
    
    Args:
        topic: The research question or topic to investigate.
                Should be detailed and specific for best results.
        max_depth: Maximum depth of research (number of sub-agent levels).
                   Default is 3.
        max_iterations: Maximum number of research iterations.
                        If None, uses default from config.
        timeout: Maximum time in seconds to wait for research completion.
                 If None, uses default from config.
    
    Returns:
        ResearchResult containing:
        - findings: Compressed research summary
        - sources: List of SourceInfo with URLs and snippets
        - raw_notes: Unprocessed notes for reference
        - research_brief: Original research topic
    
    Raises:
        asyncio.TimeoutError: If research exceeds timeout
        Exception: For other research failures
    
    Example:
        ```python
        from agents.deep_researcher import run_research
        
        result = await run_research(
            topic="What are the latest developments in LLM agents?",
            max_depth=2,
            timeout=300.0
        )
        
        print(f"Found {len(result.sources)} sources")
        print(result.findings[:500])
        ```
    """
    config = ResearchConfig.from_settings()
    
    # Use config defaults if not specified
    if max_iterations is None:
        max_iterations = config.MAX_RESEARCHER_ITERATIONS
    if timeout is None:
        timeout = config.DEFAULT_TIMEOUT
    
    logger.info(
        f"Starting research: topic='{topic[:50]}...', "
        f"max_depth={max_depth}, max_iterations={max_iterations}, "
        f"timeout={timeout}s"
    )
    
    try:
        # Execute with timeout
        result = await asyncio.wait_for(
            execute_research(topic, max_iterations),
            timeout=timeout
        )
        
        logger.info(
            f"Research completed successfully: "
            f"{len(result.sources)} sources, "
            f"{len(result.findings)} chars in findings"
        )
        
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"Research timed out after {timeout}s")
        raise
    except Exception as e:
        logger.error(f"Research failed: {e}")
        raise


def run_research_sync(
    topic: str,
    max_depth: int = 3,
    max_iterations: int | None = None,
    timeout: float | None = None,
) -> ResearchResult:
    """
    Synchronous wrapper for run_research.
    
    Use this when you need to call from synchronous code.
    For async code, prefer run_research() directly.
    
    Args:
        Same as run_research()
    
    Returns:
        Same as run_research()
    """
    return asyncio.run(
        run_research(topic, max_depth, max_iterations, timeout)
    )
