"""
Conference utility functions

Helper functions for text processing and data manipulation.
"""

from typing import List, Optional, Dict
from collections import Counter


def split_comma_values(field_value: Optional[str]) -> List[str]:
    """Split comma-separated values and filter out blanks

    Handles malformed data like:
    - "A,,B" (double commas) -> ["A", "B"]
    - ",A,B" (leading comma) -> ["A", "B"]
    - "A,B," (trailing comma) -> ["A", "B"]
    - "A, ,B" (spaces only) -> ["A", "B"]
    - "  A  ,  B  " (extra whitespace) -> ["A", "B"]

    Args:
        field_value: String with comma-separated values

    Returns:
        List of cleaned string values
    """
    if not field_value:
        return []
    return [item.strip() for item in field_value.split(',') if item.strip()]


def split_semicolon_values(field_value: Optional[str]) -> List[str]:
    """Split semicolon-separated values and filter out blanks

    Handles malformed data like:
    - "A;;B" (double semicolons) -> ["A", "B"]
    - ";A;B" (leading semicolon) -> ["A", "B"]
    - "A;B;" (trailing semicolon) -> ["A", "B"]

    Args:
        field_value: String with semicolon-separated values

    Returns:
        List of cleaned string values
    """
    if not field_value:
        return []
    return [item.strip() for item in field_value.split(';') if item.strip()]


def split_by_separator(field_value: Optional[str], separator: str = ',') -> List[str]:
    """Split values by custom separator and filter out blanks

    Args:
        field_value: String with separated values
        separator: Character to split on

    Returns:
        List of cleaned string values
    """
    if not field_value:
        return []
    return [item.strip() for item in field_value.split(separator) if item.strip()]


def join_values(values: List[str], separator: str = ',') -> str:
    """Join list of values with separator, filtering out empty values

    Args:
        values: List of string values
        separator: Character to join with

    Returns:
        Joined string
    """
    if not values:
        return ''
    # Filter out empty values and strip whitespace
    clean_values = [str(value).strip() for value in values if str(value).strip()]
    return separator.join(clean_values)


def deduplicate_keywords(keywords: List[str]) -> Dict[str, int]:
    """Deduplicate keywords that are case-insensitive variants of the same term

    Examples:
    - "LLM", "llm", "LLMs", "llms" -> all counted as "LLM" (most frequent original form)
    - "AI", "ai", "Ai" -> all counted as "AI"
    - "Machine Learning", "machine learning", "MACHINE LEARNING" -> "Machine Learning"

    Args:
        keywords: List of keyword strings

    Returns:
        Dictionary mapping canonical keyword to total count
    """
    if not keywords:
        return {}

    def normalize_keyword(keyword: str) -> str:
        """Normalize keyword for comparison (lowercase, remove plural 's')"""
        normalized = keyword.lower().strip()
        # Simple plural handling - remove trailing 's' if it makes sense
        if len(normalized) > 3 and normalized.endswith('s') and not normalized.endswith('ss'):
            # Don't remove 's' from words that end in 'ss', 'us', 'is', etc.
            if not any(normalized.endswith(suffix) for suffix in ['ss', 'us', 'is', 'os', 'as']):
                # Check if removing 's' creates a meaningful word (basic heuristic)
                singular = normalized[:-1]
                if len(singular) >= 2:  # Ensure we don't create single-letter words
                    normalized = singular
        return normalized

    # Step 1: Normalize and group variants
    variant_groups = {}  # normalized -> list of original forms
    for keyword in keywords:
        normalized = normalize_keyword(keyword)
        if normalized:
            if normalized not in variant_groups:
                variant_groups[normalized] = []
            variant_groups[normalized].append(keyword)

    # Step 2: For each group, pick the canonical form and sum counts
    canonical_counts = {}
    for normalized, variants in variant_groups.items():
        # Count occurrences of each variant
        variant_counter = Counter(variants)

        # Pick the most frequent variant as canonical
        # Preference: most frequent > shorter form > alphabetically first
        canonical_form = max(variant_counter.keys(),
                           key=lambda x: (variant_counter[x], -len(x), x.lower()))

        # Sum all counts for this normalized form
        total_count = sum(variant_counter.values())
        canonical_counts[canonical_form] = total_count

    return canonical_counts