"""
Utility functions for RAG agent.

Provides message windowing, text extraction, and other helper functions for ReAct pattern.
"""

import logging
import re
from typing import Any, Sequence

import tiktoken
from langchain_core.messages import BaseMessage, SystemMessage

from .prompts import BEGIN_SEARCH_QUERY, BEGIN_SEARCH_RESULT, END_SEARCH_QUERY, END_SEARCH_RESULT

logger = logging.getLogger(__name__)


def get_chat_history_window(
    messages: Sequence[BaseMessage],
    max_tokens: int = 4000,
    model_name: str = "gpt-4",
) -> list[BaseMessage]:
    """
    Trim message history to fit within token budget.

    Strategy:
    - Always keep system messages (not counted toward budget)
    - Always keep the last user message
    - Fill remaining budget with recent messages (LIFO)

    This ensures we:
    1. Never lose critical context (system prompts, current question)
    2. Maximize recent context relevance
    3. Stay within model token limits

    Args:
        messages: Full message history
        max_tokens: Maximum token budget for messages
        model_name: Model name for tokenization (e.g., "gpt-4", "gpt-4.1-mini")

    Returns:
        Trimmed message list that fits within token budget

    Example:
        >>> messages = [
        ...     SystemMessage(content="You are a helpful assistant"),
        ...     HumanMessage(content="What is Python?"),
        ...     AIMessage(content="Python is a programming language..."),
        ...     HumanMessage(content="Tell me more")
        ... ]
        >>> windowed = get_chat_history_window(messages, max_tokens=100)
        >>> # Returns: [SystemMessage, HumanMessage("Tell me more")]
    """
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        # Fallback to cl100k_base if model not found
        logger.warning(f"Model {model_name} not found, using cl100k_base encoding")
        encoding = tiktoken.get_encoding("cl100k_base")

    # Separate system messages from others
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

    if not other_msgs:
        # Only system messages, return as-is
        return system_msgs

    # Always keep last message (current user question)
    last_msg = other_msgs[-1]
    remaining_msgs = other_msgs[:-1]

    # Count tokens for required messages (system + last)
    required_tokens = 0
    for msg in [*system_msgs, last_msg]:
        try:
            required_tokens += len(encoding.encode(str(msg.content)))
        except Exception as e:
            logger.warning(f"Error encoding message: {e}")
            # Rough estimate: 4 chars per token
            required_tokens += len(str(msg.content)) // 4

    if required_tokens >= max_tokens:
        # Critical: Can only fit system messages + last message
        logger.warning(
            f"Required messages ({required_tokens} tokens) exceed budget ({max_tokens} tokens)"
        )
        return system_msgs + [last_msg]

    # Add messages from recent to old within remaining budget
    budget = max_tokens - required_tokens
    windowed = []

    for msg in reversed(remaining_msgs):
        try:
            msg_tokens = len(encoding.encode(str(msg.content)))
        except Exception as e:
            logger.warning(f"Error encoding message: {e}")
            msg_tokens = len(str(msg.content)) // 4

        if msg_tokens <= budget:
            windowed.insert(0, msg)
            budget -= msg_tokens
        else:
            # Can't fit this message, stop
            break

    final_messages = system_msgs + windowed + [last_msg]

    logger.info(
        f"Windowed {len(messages)} messages to {len(final_messages)} "
        f"(budget: {max_tokens} tokens, used: ~{max_tokens - budget} tokens)"
    )

    return final_messages


def estimate_token_count(text: str, model_name: str = "gpt-4") -> int:
    """
    Estimate token count for a text string.

    Args:
        text: Text to count tokens for
        model_name: Model name for tokenization

    Returns:
        Estimated token count
    """
    try:
        encoding = tiktoken.encoding_for_model(model_name)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Error estimating tokens: {e}")
        # Rough estimate: 4 chars per token
        return len(text) // 4


# ===== ReAct Pattern Utilities =====


def extract_between(text: str, start_tag: str, end_tag: str) -> list[str]:
    """
    Extract all text segments between start and end tags.

    Based on DeepResearcher's implementation for extracting search queries
    and results from LLM output.

    Args:
        text: Text to search within
        start_tag: Opening tag (e.g., "<|begin_search_query|>")
        end_tag: Closing tag (e.g., "<|end_search_query|>")

    Returns:
        List of extracted text segments (without tags)

    Example:
        >>> text = "some text <|begin_search_query|>query1<|end_search_query|> more <|begin_search_query|>query2<|end_search_query|>"
        >>> extract_between(text, "<|begin_search_query|>", "<|end_search_query|>")
        ['query1', 'query2']
    """
    pattern = re.escape(start_tag) + r"(.*?)" + re.escape(end_tag)
    matches = re.findall(pattern, text, re.DOTALL)
    # Strip whitespace from each match
    return [m.strip() for m in matches if m.strip()]


def remove_tags(text: str, start_tag: str, end_tag: str) -> str:
    """
    Remove all occurrences of tagged content (including tags).

    Args:
        text: Text to process
        start_tag: Opening tag
        end_tag: Closing tag

    Returns:
        Text with all tagged segments removed

    Example:
        >>> text = "Keep this <|tag|>remove this<|/tag|> keep this"
        >>> remove_tags(text, "<|tag|>", "<|/tag|>")
        'Keep this  keep this'
    """
    pattern = re.escape(start_tag) + r".*?" + re.escape(end_tag)
    return re.sub(pattern, "", text, flags=re.DOTALL)


def remove_query_tags(text: str) -> str:
    """
    Remove search query tags from text.

    Args:
        text: Text containing query tags

    Returns:
        Text with query tags removed
    """
    return remove_tags(text, BEGIN_SEARCH_QUERY, END_SEARCH_QUERY)


def remove_result_tags(text: str) -> str:
    """
    Remove search result tags from text.

    Args:
        text: Text containing result tags

    Returns:
        Text with result tags removed
    """
    return remove_tags(text, BEGIN_SEARCH_RESULT, END_SEARCH_RESULT)


def truncate_reasoning_history(
    reasoning_steps: list[str],
    keep_first_n: int = 1,
    keep_last_n: int = 4
) -> str:
    """
    Truncate reasoning history to maintain reasonable context length.

    Based on DeepResearcher's strategy:
    - Keep first N steps (initial reasoning)
    - Keep last N steps (recent context)
    - Add ellipsis for omitted middle steps

    Args:
        reasoning_steps: List of all reasoning steps
        keep_first_n: Number of initial steps to preserve
        keep_last_n: Number of recent steps to preserve

    Returns:
        Formatted truncated history string

    Example:
        >>> steps = ["step1", "step2", "step3", "step4", "step5", "step6"]
        >>> truncate_reasoning_history(steps, keep_first_n=1, keep_last_n=2)
        'Step 1: step1\\n\\n...\\n\\nStep 5: step5\\n\\nStep 6: step6'
    """
    if len(reasoning_steps) <= keep_first_n + keep_last_n:
        # No truncation needed
        result = ""
        for i, step in enumerate(reasoning_steps):
            result += f"Step {i + 1}: {step}\n\n"
        return result.strip()

    # Build truncated history
    truncated = ""

    # Add first N steps
    for i in range(keep_first_n):
        truncated += f"Step {i + 1}: {reasoning_steps[i]}\n\n"

    # Add ellipsis
    truncated += "...\n\n"

    # Add last N steps
    start_idx = len(reasoning_steps) - keep_last_n
    for i in range(start_idx, len(reasoning_steps)):
        truncated += f"Step {i + 1}: {reasoning_steps[i]}\n\n"

    return truncated.strip()


def format_chunks(chunks: list[dict[str, Any]], max_content_length: int = 500) -> str:
    """
    Format retrieved chunks for LLM consumption.

    Args:
        chunks: List of chunk dictionaries with keys like 'content', 'doc_name', 'similarity'
        max_content_length: Maximum characters per chunk content (truncate if longer)

    Returns:
        Formatted string with all chunks

    Example output:
        ```
        [1] Document Name (similarity: 0.92)
        Content: First 500 chars of content...

        [2] Another Document (similarity: 0.87)
        Content: First 500 chars of content...
        ```
    """
    if not chunks:
        return "No documents retrieved."

    formatted = ""
    for i, chunk in enumerate(chunks, 1):
        doc_name = chunk.get("doc_name", "Unknown Document")
        similarity = chunk.get("similarity", 0.0)
        content = chunk.get("content", "")

        # Truncate content if too long
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        formatted += f"[{i}] {doc_name} (similarity: {similarity:.2f})\n"
        formatted += f"Content: {content}\n\n"

    return formatted.strip()
