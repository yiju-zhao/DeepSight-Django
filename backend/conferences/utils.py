"""
Conference utility functions

Helper functions for text processing and data manipulation.
"""

from typing import List, Optional


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