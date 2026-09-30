"""
preprocessor.py — Text Normalization, Punctuation & Domain Abbreviation Cleaner
Cleans raw material descriptions for downstream vectorization and matching.
"""

import re
import unicodedata
from config import DOMAIN_ABBREVIATIONS


# ── Stop-words relevant to industrial / material context ──────────────
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at",
    "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "shall", "should", "would",
    "could", "may", "might", "must", "with", "by", "from", "as", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "can", "just", "but", "about", "up", "it", "its", "this",
    "that", "these", "those", "i", "me", "my", "we", "our", "you",
    "your", "he", "him", "his", "she", "her", "they", "them", "their",
})


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters to ASCII-compatible form."""
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii")


def clean_punctuation(text: str) -> str:
    """Remove extraneous punctuation while preserving meaningful separators."""
    text = re.sub(r"[\"\'`″]", " inch ", text)          # quotes → inch
    text = re.sub(r"[#]", " number ", text)             # hash → number
    text = re.sub(r"[&]", " and ", text)                # ampersand → and
    text = re.sub(r"[@]", " at ", text)
    # Replace all other punctuation with space (including hyphens and slashes)
    text = re.sub(r"[(){}\[\]\-\/,;!?~^*+=|\\<>]", " ", text)
    text = re.sub(r"\.(?!\d)", " ", text)               # dots not in numbers → space
    return text


def expand_abbreviations(text: str) -> str:
    """Replace domain-specific abbreviations with full forms."""
    tokens = text.split()
    expanded = []
    for token in tokens:
        lower = token.lower().strip(".-/")
        if lower in DOMAIN_ABBREVIATIONS:
            expanded.append(DOMAIN_ABBREVIATIONS[lower])
        else:
            expanded.append(token)
    return " ".join(expanded)


def normalize_units(text: str) -> str:
    """Normalize common unit representations."""
    # Add spaces between numbers and letters (e.g. 2in -> 2 in, dn50 -> dn 50)
    text = re.sub(r'([0-9]+)([a-zA-Z]+)', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z]+)([0-9]+)', r'\1 \2', text)
    
    # inch variants
    text = re.sub(r'\b(\d+)\s*["″\'\']\s*', r"\1 inch ", text)
    text = re.sub(r"\b(\d+)\s*in\b", r"\1 inch ", text)
    # mm variants
    text = re.sub(r"\b(\d+)\s*m\.?m\.?\b", r"\1 millimeter ", text, flags=re.IGNORECASE)
    # kg variants
    text = re.sub(r"\b(\d+)\s*k\.?g\.?\b", r"\1 kilogram ", text, flags=re.IGNORECASE)
    return text


def remove_stop_words(text: str) -> str:
    """Remove common stop-words that add no discriminative value."""
    tokens = text.split()
    return " ".join(t for t in tokens if t.lower() not in _STOP_WORDS)


def collapse_whitespace(text: str) -> str:
    """Reduce multiple whitespace characters to single space."""
    return re.sub(r"\s+", " ", text).strip()


def preprocess(text: str) -> str:
    """
    Full preprocessing pipeline for a single material description.
    Returns a cleaned, normalized string.
    """
    if not text or not isinstance(text, str):
        return ""
    text = normalize_unicode(text)
    text = text.lower()
    text = clean_punctuation(text)
    text = normalize_units(text)
    text = expand_abbreviations(text)
    text = remove_stop_words(text)
    text = collapse_whitespace(text)
    return text


def preprocess_batch(texts: list[str]) -> list[str]:
    """Apply preprocessing pipeline to a list of texts."""
    return [preprocess(t) for t in texts]
