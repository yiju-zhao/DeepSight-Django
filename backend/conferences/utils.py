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


def build_cooccurrence_matrix(items_per_publication: List[List[str]], top_n: int = 10) -> Dict:
    """Build co-occurrence matrix for chord diagrams

    Args:
        items_per_publication: List of lists, where each inner list contains unique items for one publication
        top_n: Number of top items to include in the matrix

    Returns:
        Dictionary with:
        - keys: ordered list of top N item names
        - matrix: NxN symmetric matrix with co-occurrence counts
        - totals: total unique paper count per item (for reference)
    """
    if not items_per_publication:
        return {'keys': [], 'matrix': [], 'totals': {}}

    # Count total unique paper participation per item
    item_totals = Counter()
    pair_counts = Counter()

    for items in items_per_publication:
        # Convert to set to ensure uniqueness within publication
        unique_items = set(items)

        # Count each item's participation in this publication
        for item in unique_items:
            item_totals[item] += 1

        # Count pairs within this publication
        items_list = list(unique_items)
        for i, item1 in enumerate(items_list):
            for j, item2 in enumerate(items_list):
                if i < j:  # Only count each pair once (unordered)
                    # Use sorted tuple to ensure consistent ordering
                    pair_key = tuple(sorted([item1, item2]))
                    pair_counts[pair_key] += 1

    # Select top N items by total participation
    top_items = [item for item, count in item_totals.most_common(top_n)]

    if not top_items:
        return {'keys': [], 'matrix': [], 'totals': {}}

    # Build symmetric matrix
    n = len(top_items)
    matrix = [[0 for _ in range(n)] for _ in range(n)]

    # Fill matrix with pair counts
    for i, item1 in enumerate(top_items):
        for j, item2 in enumerate(top_items):
            if i != j:
                pair_key = tuple(sorted([item1, item2]))
                count = pair_counts.get(pair_key, 0)
                matrix[i][j] = count
            # Diagonal can represent self-count or be 0
            # For chord diagrams, we typically set diagonal to 0
            else:
                matrix[i][j] = 0

    return {
        'keys': top_items,
        'matrix': matrix,
        'totals': dict(item_totals)
    }


def build_fine_histogram(values: List[float], bin_size: float = 0.5, min_val: float = None, max_val: float = None) -> List[Dict]:
    """Build fine-grained histogram with configurable bin size

    Args:
        values: List of numeric values to bin
        bin_size: Size of each bin (default 0.5)
        min_val: Minimum value for binning (default: min of values)
        max_val: Maximum value for binning (default: max of values)

    Returns:
        List of dictionaries with bin info: [{'bin': center, 'start': start, 'end': end, 'count': count}]
    """
    if not values:
        return []

    # Filter out None values and convert to floats
    clean_values = [float(v) for v in values if v is not None]
    if not clean_values:
        return []

    # Determine range
    if min_val is None:
        min_val = min(clean_values)
    if max_val is None:
        max_val = max(clean_values)

    # Clamp bin_size to reasonable bounds
    bin_size = max(0.1, min(2.0, bin_size))

    # Generate bins
    bins = []
    current_start = min_val

    while current_start < max_val:
        current_end = min(current_start + bin_size, max_val + bin_size)  # Allow for edge cases
        bins.append({
            'start': current_start,
            'end': current_end,
            'bin': current_start + bin_size / 2,  # Center of bin
            'count': 0
        })
        current_start = current_end

    # Count values in each bin
    for value in clean_values:
        for bin_info in bins:
            if bin_info['start'] <= value < bin_info['end'] or (value == max_val and bin_info['end'] > max_val):
                bin_info['count'] += 1
                break

    # Remove empty bins at the end if desired
    # Keep all bins for now to show complete range

    return bins