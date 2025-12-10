"""
LangGraph Entry Point for Deep Researcher Agent

This module provides the compiled research graph and the main entry point
for executing research workflows.
"""

import logging
from typing import Optional, List

from langchain_core.messages import HumanMessage

from .states import ResearchResult, SourceInfo, SupervisorState
from .supervisor import get_supervisor_agent, get_notes_from_tool_calls


logger = logging.getLogger(__name__)


def extract_sources_from_notes(notes: List[str]) -> List[SourceInfo]:
    """
    Extract source information from research notes.
    
    Parses the notes to find URLs and their associated metadata.
    
    Args:
        notes: List of research notes containing source references
        
    Returns:
        List of SourceInfo objects
    """
    sources = []
    seen_urls = set()
    
    for note in notes:
        # Simple URL extraction - look for common patterns
        import re
        url_pattern = r'(?:URL:|Source:|\[[\d]+\])\s*(https?://[^\s\)]+)'
        matches = re.findall(url_pattern, note)
        
        for url in matches:
            url = url.rstrip('.,;:')
            if url not in seen_urls:
                seen_urls.add(url)
                
                # Try to extract title (look for patterns like "Title: ...")
                title_match = re.search(rf'(?:---\s*SOURCE\s*\d+:\s*|Title:\s*)([^\n]+)\s*---?\s*\n.*?{re.escape(url)}', note, re.DOTALL)
                title = title_match.group(1).strip() if title_match else "Source"
                
                # Extract a snippet around the URL
                url_pos = note.find(url)
                snippet_start = max(0, url_pos - 200)
                snippet_end = min(len(note), url_pos + 200)
                snippet = note[snippet_start:snippet_end].strip()
                
                sources.append(SourceInfo(
                    url=url,
                    title=title,
                    snippet=snippet[:500] if len(snippet) > 500 else snippet
                ))
    
    return sources


async def run_research_graph(
    research_brief: str,
    max_iterations: Optional[int] = None,
) -> dict:
    """
    Execute the research graph with the given brief.
    
    This is the low-level graph execution function that returns raw results.
    
    Args:
        research_brief: The research question or topic to investigate
        max_iterations: Optional maximum number of research iterations
        
    Returns:
        Dictionary with research results from the graph
    """
    supervisor = get_supervisor_agent()
    
    initial_state: SupervisorState = {
        "supervisor_messages": [HumanMessage(content=research_brief)],
        "research_brief": research_brief,
        "notes": [],
        "research_iterations": 0,
        "raw_notes": [],
    }
    
    try:
        result = await supervisor.ainvoke(initial_state)
        return result
    except Exception as e:
        logger.error(f"Research graph execution failed: {e}")
        raise


def compile_research_result(graph_output: dict, research_brief: str) -> ResearchResult:
    """
    Compile graph output into a structured ResearchResult.
    
    Args:
        graph_output: Raw output from the research graph
        research_brief: Original research query
        
    Returns:
        ResearchResult with findings, sources, and raw notes
    """
    notes = graph_output.get("notes", [])
    raw_notes = graph_output.get("raw_notes", [])
    
    # Compile findings from notes
    findings = "\n\n".join(notes) if notes else "No findings available."
    
    # Extract sources from notes
    all_notes = notes + raw_notes
    sources = extract_sources_from_notes(all_notes)
    
    return ResearchResult(
        findings=findings,
        sources=sources,
        raw_notes=raw_notes,
        research_brief=research_brief
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def execute_research(
    topic: str,
    max_iterations: Optional[int] = None,
) -> ResearchResult:
    """
    Execute a complete research workflow.
    
    This is the main entry point for the research graph, returning
    a structured ResearchResult that can be passed to the report_writer.
    
    Args:
        topic: The research question or topic to investigate
        max_iterations: Optional maximum number of research iterations
        
    Returns:
        ResearchResult with findings, sources, and raw notes
    """
    logger.info(f"Starting research on topic: {topic[:100]}...")
    
    graph_output = await run_research_graph(topic, max_iterations)
    result = compile_research_result(graph_output, topic)
    
    logger.info(f"Research complete. Found {len(result.sources)} sources.")
    
    return result
