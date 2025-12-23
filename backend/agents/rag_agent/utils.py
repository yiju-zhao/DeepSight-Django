"""
Utility functions for RAG agent.

Provides message windowing, text extraction, and other helper functions for ReAct pattern.
"""

import logging
import re
from typing import Any, Sequence

import tiktoken
from langchain_core.messages import BaseMessage, SystemMessage


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


def format_tool_content(content: Any) -> str:
    """
    Normalize tool message content (which may be structured) into plain text.
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            formatted = format_tool_content(item)
            if formatted:
                parts.append(formatted)
        return "\n".join(parts)

    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        if "content" in content:
            return format_tool_content(content.get("content"))
        if isinstance(content.get("data"), str):
            return content["data"]

    if hasattr(content, "text") and isinstance(getattr(content, "text"), str):
        return getattr(content, "text")

    return str(content)
