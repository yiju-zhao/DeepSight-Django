"""
Writer Workflow for Report Writer Agent

This module implements the writing workflow that transforms
research findings into polished reports.
"""

import logging
import re
from datetime import datetime

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from django.conf import settings

from .states import WriterResult, Section


logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


def get_writer_model():
    """Get the configured writer model."""
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    model_name = getattr(settings, "WRITER_MODEL", "gpt-4.1")
    max_tokens = getattr(settings, "WRITER_MAX_TOKENS", 32000)

    return init_chat_model(
        model=f"openai:{model_name}",
        api_key=api_key,
        max_tokens=max_tokens,
    )


def get_today_str() -> str:
    """Get current date in human-readable format."""
    return datetime.now().strftime("%B %d, %Y")


# ============================================================================
# PARSING UTILITIES
# ============================================================================


def parse_sections(report: str) -> list[Section]:
    """
    Parse a markdown report into sections.

    Args:
        report: Markdown report content

    Returns:
        List of Section objects
    """
    sections = []

    # Split by headings
    heading_pattern = r"^(#{1,4})\s+(.+)$"
    lines = report.split("\n")

    current_section = None
    current_content = []

    for line in lines:
        match = re.match(heading_pattern, line)
        if match:
            # Save previous section
            if current_section:
                current_section.content = "\n".join(current_content).strip()
                sections.append(current_section)

            # Start new section
            level = len(match.group(1))
            title = match.group(2).strip()
            current_section = Section(title=title, content="", level=level)
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_section:
        current_section.content = "\n".join(current_content).strip()
        sections.append(current_section)

    return sections


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def detect_language(text: str) -> str:
    """
    Simple language detection based on character analysis.

    Args:
        text: Text to analyze

    Returns:
        Language code (e.g., 'en', 'zh', 'ja')
    """
    # Count Chinese characters
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    # Count Japanese-specific characters
    japanese_chars = len(re.findall(r"[\u3040-\u309f\u30a0-\u30ff]", text))
    # Count total characters (excluding whitespace)
    total_chars = len(re.findall(r"\S", text))

    if total_chars == 0:
        return "en"

    chinese_ratio = chinese_chars / total_chars
    japanese_ratio = japanese_chars / total_chars

    if japanese_ratio > 0.1:
        return "ja"
    elif chinese_ratio > 0.1:
        return "zh"
    else:
        return "en"


# ============================================================================
# WRITING FUNCTIONS
# ============================================================================


async def generate_report(
    research_brief: str,
    findings: str,
    sources: list[dict],
    style: str = "academic",
    draft_outline: str | None = None,
) -> str:
    """
    Generate a report from research findings.

    Args:
        research_brief: Original research question
        findings: Compressed research findings
        sources: List of source information
        style: Writing style
        draft_outline: Optional outline to follow

    Returns:
        Generated report in markdown format
    """
    from .prompts import report_generation_prompt, get_style_instructions

    model = get_writer_model()

    # Build the prompt
    style_instructions = get_style_instructions(style)

    # Format sources for inclusion
    sources_text = (
        "\n".join(
            [
                f"- [{s.get('title', 'Source')}]({s.get('url', '')}): {s.get('snippet', '')[:200]}"
                for s in sources
            ]
        )
        if sources
        else "No sources available."
    )

    # Combine findings with sources
    full_findings = f"{findings}\n\n### Available Sources:\n{sources_text}"

    prompt = report_generation_prompt.format(
        research_brief=research_brief,
        findings=full_findings,
        date=get_today_str(),
    )

    # Add style instructions
    full_prompt = f"{style_instructions}\n\n{prompt}"

    # Add outline if provided
    if draft_outline:
        full_prompt = f"Follow this outline:\n{draft_outline}\n\n{full_prompt}"

    try:
        response = await model.ainvoke([HumanMessage(content=full_prompt)])
        return response.content
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise


async def polish_report(
    draft_report: str,
    research_brief: str,
) -> str:
    """
    Polish and refine a draft report.

    Args:
        draft_report: Draft report to polish
        research_brief: Original research question

    Returns:
        Polished report in markdown format
    """
    from .prompts import polish_report_prompt

    model = get_writer_model()

    prompt = polish_report_prompt.format(
        draft_report=draft_report,
        research_brief=research_brief,
    )

    try:
        response = await model.ainvoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        logger.error(f"Report polishing failed: {e}")
        return draft_report  # Return original if polishing fails


# ============================================================================
# MAIN WRITING WORKFLOW
# ============================================================================


async def write_report(
    research_brief: str,
    findings: str,
    sources: list[dict],
    style: str = "academic",
    draft_outline: str | None = None,
    polish: bool = True,
) -> WriterResult:
    """
    Execute the complete writing workflow.

    Args:
        research_brief: Original research question
        findings: Compressed research findings
        sources: List of source information
        style: Writing style
        draft_outline: Optional outline to follow
        polish: Whether to polish the report

    Returns:
        WriterResult with final report and metadata
    """
    logger.info(f"Starting report generation for: {research_brief[:50]}...")

    # Generate initial report
    report = await generate_report(
        research_brief=research_brief,
        findings=findings,
        sources=sources,
        style=style,
        draft_outline=draft_outline,
    )

    # Polish if requested
    if polish:
        logger.info("Polishing report...")
        report = await polish_report(report, research_brief)

    # Parse sections
    sections = parse_sections(report)

    # Calculate word count
    word_count = count_words(report)

    # Detect language
    language = detect_language(report)

    logger.info(
        f"Report complete: {word_count} words, {len(sections)} sections, language: {language}"
    )

    return WriterResult(
        final_report=report,
        sections=sections,
        word_count=word_count,
        language=language,
    )
