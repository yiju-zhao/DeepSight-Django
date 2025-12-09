"""
Utility functions for RAG agent.

Provides message windowing and other helper functions.
"""

import logging
from typing import Sequence

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
        model_name: Model name for tokenization (e.g., "gpt-4", "gpt-4o-mini")

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
