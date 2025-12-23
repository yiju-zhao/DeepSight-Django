"""
Public Interface for Report Writer Agent

This module provides the public async API for the report writer,
suitable for use by the coordinator or direct API calls.
"""

import asyncio
import logging

from .states import WriterResult
from .writer import write_report


logger = logging.getLogger(__name__)


async def run_writer(
    research_brief: str,
    findings: str,
    sources: list[dict] | None = None,
    draft_outline: str | None = None,
    style: str = "academic",
    polish: bool = True,
    timeout: float | None = None,
) -> WriterResult:
    """
    Generate a polished report from research findings.

    This is the main public interface for the report_writer module.
    It takes research output (typically from deep_researcher) and
    produces a well-formatted report.

    Args:
        research_brief: The original research question or topic.
        findings: Compressed research findings from the researcher.
        sources: List of source dictionaries with 'url', 'title', 'snippet'.
                 If None, empty list is used.
        draft_outline: Optional outline to guide report structure.
        style: Writing style to use:
               - 'academic': Formal, well-cited, objective
               - 'casual': Conversational, accessible
               - 'technical': Precise, detailed, technical focus
               - 'business': Executive summary format, actionable
        polish: Whether to run a polishing pass. Default True.
        timeout: Maximum time in seconds to wait for completion.
                 If None, no timeout is applied.

    Returns:
        WriterResult containing:
        - final_report: Complete report in markdown
        - sections: Parsed sections of the report
        - word_count: Total word count
        - language: Detected language code

    Raises:
        asyncio.TimeoutError: If writing exceeds timeout
        Exception: For other writing failures

    Example:
        ```python
        from agents.report_writer import run_writer
        from agents.deep_researcher import run_research

        # First, do research
        research = await run_research("Latest AI developments")

        # Then, generate report
        report = await run_writer(
            research_brief=research.research_brief,
            findings=research.findings,
            sources=[s.dict() for s in research.sources],
            style="academic"
        )

        print(report.final_report)
        ```
    """
    if sources is None:
        sources = []

    logger.info(
        f"Starting report writing: brief='{research_brief[:50]}...', "
        f"style={style}, polish={polish}"
    )

    try:
        if timeout:
            result = await asyncio.wait_for(
                write_report(
                    research_brief=research_brief,
                    findings=findings,
                    sources=sources,
                    style=style,
                    draft_outline=draft_outline,
                    polish=polish,
                ),
                timeout=timeout,
            )
        else:
            result = await write_report(
                research_brief=research_brief,
                findings=findings,
                sources=sources,
                style=style,
                draft_outline=draft_outline,
                polish=polish,
            )

        logger.info(
            f"Report writing completed: "
            f"{result.word_count} words, {len(result.sections)} sections"
        )

        return result

    except asyncio.TimeoutError:
        logger.error(f"Report writing timed out after {timeout}s")
        raise
    except Exception as e:
        logger.error(f"Report writing failed: {e}")
        raise


def run_writer_sync(
    research_brief: str,
    findings: str,
    sources: list[dict] | None = None,
    draft_outline: str | None = None,
    style: str = "academic",
    polish: bool = True,
    timeout: float | None = None,
) -> WriterResult:
    """
    Synchronous wrapper for run_writer.

    Use this when you need to call from synchronous code.
    For async code, prefer run_writer() directly.

    Args:
        Same as run_writer()

    Returns:
        Same as run_writer()
    """
    return asyncio.run(
        run_writer(
            research_brief=research_brief,
            findings=findings,
            sources=sources,
            draft_outline=draft_outline,
            style=style,
            polish=polish,
            timeout=timeout,
        )
    )
