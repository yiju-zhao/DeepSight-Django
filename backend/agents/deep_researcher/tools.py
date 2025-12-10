"""
Research Tools for Deep Researcher Agent

This module provides search and content processing tools for the research agent,
including web search capabilities via Tavily and strategic reflection tools.

Note: Report writing tools (refine_draft_report) are in report_writer module.
"""

import logging
from typing import List, Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool, InjectedToolArg
from typing_extensions import Annotated
from tavily import TavilyClient

from .config import get_tavily_api_key, get_today_str, ResearchConfig
from .states import Summary
from .prompts import summarize_webpage_prompt


logger = logging.getLogger(__name__)


# ============================================================================
# LAZY INITIALIZATION (Models and clients initialized on first use)
# ============================================================================

_summarization_model = None
_tavily_client = None


def _get_summarization_model():
    """Lazy initialization of summarization model."""
    global _summarization_model
    if _summarization_model is None:
        from .config import get_model_config
        config = get_model_config()
        _summarization_model = init_chat_model(
            model=f"openai:{config['model']}",
            api_key=config['api_key'],
        )
    return _summarization_model


def _get_tavily_client():
    """Lazy initialization of Tavily client."""
    global _tavily_client
    if _tavily_client is None:
        api_key = get_tavily_api_key()
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


# ============================================================================
# SEARCH FUNCTIONS
# ============================================================================

def tavily_search_multiple(
    search_queries: List[str],
    max_results: int = 3,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,
) -> List[dict]:
    """
    Perform search using Tavily API for multiple queries.

    Args:
        search_queries: List of search queries to execute
        max_results: Maximum number of results per query
        topic: Topic filter for search results
        include_raw_content: Whether to include raw webpage content

    Returns:
        List of search result dictionaries
    """
    client = _get_tavily_client()
    search_docs = []
    
    for query in search_queries:
        try:
            result = client.search(
                query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic
            )
            search_docs.append(result)
        except Exception as e:
            logger.warning(f"Search failed for query '{query}': {e}")
            search_docs.append({"results": []})
    
    return search_docs


def summarize_webpage_content(webpage_content: str) -> str:
    """
    Summarize webpage content using the configured summarization model.

    Args:
        webpage_content: Raw webpage content to summarize

    Returns:
        Formatted summary with key excerpts
    """
    try:
        model = _get_summarization_model()
        structured_model = model.with_structured_output(Summary)

        summary = structured_model.invoke([
            HumanMessage(content=summarize_webpage_prompt.format(
                webpage_content=webpage_content,
                date=get_today_str()
            ))
        ])

        formatted_summary = (
            f"<summary>\n{summary.summary}\n</summary>\n\n"
            f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
        )

        return formatted_summary

    except Exception as e:
        logger.warning(f"Failed to summarize webpage: {e}")
        return webpage_content[:1000] + "..." if len(webpage_content) > 1000 else webpage_content


def deduplicate_search_results(search_results: List[dict]) -> dict:
    """
    Deduplicate search results by URL to avoid processing duplicate content.

    Args:
        search_results: List of search result dictionaries

    Returns:
        Dictionary mapping URLs to unique results
    """
    unique_results = {}

    for response in search_results:
        for result in response.get('results', []):
            url = result.get('url')
            if url and url not in unique_results:
                unique_results[url] = result

    return unique_results


def process_search_results(unique_results: dict) -> dict:
    """
    Process search results by summarizing content where available.

    Args:
        unique_results: Dictionary of unique search results

    Returns:
        Dictionary of processed results with summaries
    """
    config = ResearchConfig()
    summarized_results = {}

    for url, result in unique_results.items():
        if not result.get("raw_content"):
            content = result.get('content', '')
        else:
            # Summarize raw content for better processing
            content = summarize_webpage_content(
                result['raw_content'][:config.MAX_CONTEXT_LENGTH]
            )

        summarized_results[url] = {
            'title': result.get('title', 'Untitled'),
            'content': content
        }

    return summarized_results


def format_search_output(summarized_results: dict) -> str:
    """
    Format search results into a well-structured string output.

    Args:
        summarized_results: Dictionary of processed search results

    Returns:
        Formatted string of search results with clear source separation
    """
    if not summarized_results:
        return "No valid search results found. Please try different search queries."

    formatted_output = "Search results: \n\n"

    for i, (url, result) in enumerate(summarized_results.items(), 1):
        formatted_output += f"\n\n--- SOURCE {i}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result['content']}\n\n"
        formatted_output += "-" * 80 + "\n"

    return formatted_output


# ============================================================================
# RESEARCH TOOLS (LangChain tool definitions)
# ============================================================================

@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 3,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
) -> str:
    """
    Fetch results from Tavily search API with content summarization.

    Args:
        query: A single search query to execute
        max_results: Maximum number of results to return
        topic: Topic to filter results by ('general', 'news', 'finance')

    Returns:
        Formatted string of search results with summaries
    """
    # Execute search for single query
    search_results = tavily_search_multiple(
        [query],
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
    )

    # Deduplicate results by URL
    unique_results = deduplicate_search_results(search_results)

    # Process results with summarization
    summarized_results = process_search_results(unique_results)

    # Format output for consumption
    return format_search_output(summarized_results)


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """
    Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    logger.debug(f"Research reflection: {reflection[:200]}...")
    return f"Reflection recorded: {reflection}"


# ============================================================================
# TOOL REGISTRY
# ============================================================================

# Available tools for research worker
RESEARCH_TOOLS = [tavily_search, think_tool]
TOOLS_BY_NAME = {tool.name: tool for tool in RESEARCH_TOOLS}
