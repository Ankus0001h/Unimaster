"""
schema_mapper.py — Dynamic AI Column Auto-Segregation & Mapper
Maps arbitrary CSV/Excel column headers to the platform's standard schema
using fuzzy keyword matching with confidence scores.
"""

from rapidfuzz import fuzz, process
from config import STANDARD_FIELDS, COLUMN_KEYWORD_MAP


def _score_column(header: str, target_field: str) -> float:
    """
    Score how well a column header matches a target standard field.
    Uses max similarity across all keywords for that field.
    """
    header_lower = header.lower().strip().replace(" ", "_")
    keywords = COLUMN_KEYWORD_MAP.get(target_field, [])

    if not keywords:
        return 0.0

    # Exact match shortcut
    if header_lower == target_field:
        return 100.0
    if header_lower in keywords:
        return 99.0

    # Fuzzy match against all keywords
    best = 0.0
    for kw in keywords:
        # Token sort handles word order differences
        token_score = fuzz.token_sort_ratio(header_lower, kw)
        # Partial ratio handles substring matches
        partial_score = fuzz.partial_ratio(header_lower, kw)
        # Weighted blend
        score = 0.6 * token_score + 0.4 * partial_score
        best = max(best, score)

    return best


def auto_map_columns(headers: list[str]) -> dict:
    """
    Given a list of column headers from an uploaded file, map each to the
    closest standard field with a confidence score.

    Returns:
        {
            "mappings": {
                "original_header": {
                    "mapped_to": "standard_field",
                    "confidence": 87.5
                },
                ...
            },
            "unmapped": ["col_name_1", ...],
            "logs": ["[AI MAPPER]: ..."]
        }
    """
    mappings = {}
    unmapped = []
    logs = []
    used_fields = set()

    # Score all combinations
    score_matrix = []
    for header in headers:
        for field in STANDARD_FIELDS:
            score = _score_column(header, field)
            score_matrix.append((header, field, score))

    # Sort descending by score — greedy assignment
    score_matrix.sort(key=lambda x: x[2], reverse=True)

    mapped_headers = set()

    for header, field, score in score_matrix:
        if header in mapped_headers or field in used_fields:
            continue
        if score >= 50:  # minimum confidence threshold
            mappings[header] = {
                "mapped_to": field,
                "confidence": round(score, 1),
            }
            used_fields.add(field)
            mapped_headers.add(header)
            logs.append(
                f"[AI MAPPER]: Auto-mapping column '{header}' -> "
                f"'{field}' [CONFIDENCE: {score:.0f}%]"
            )

    # Anything not mapped
    for header in headers:
        if header not in mapped_headers:
            unmapped.append(header)
            logs.append(
                f"[AI MAPPER]: Column '{header}' could not be mapped "
                f"(no match above 50% confidence)"
            )

    return {
        "mappings": mappings,
        "unmapped": unmapped,
        "logs": logs,
    }


def rename_dataframe_columns(df, mapping_result: dict):
    """
    Rename a pandas DataFrame's columns based on the mapping result.
    Returns a new DataFrame with renamed columns.
    """
    rename_map = {}
    for original, info in mapping_result["mappings"].items():
        rename_map[original] = info["mapped_to"]

    return df.rename(columns=rename_map)
