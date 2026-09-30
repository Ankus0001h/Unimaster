"""
code_generator.py — Dynamic Common National Material Code (CNMC) Generator
Generates unique national codes for clustered material groups based on
extracted attributes and categories.
"""

import re
import hashlib
from config import CNMC_PREFIX, CNMC_START_SEQ


# ── Material Category Detection ──────────────────────────────────────

_CATEGORY_KEYWORDS = {
    "STEEL":      ["steel", "stainless", "carbon steel", "mild steel", "alloy steel"],
    "PIPE":       ["pipe", "tube", "tubing", "piping", "conduit"],
    "VALVE":      ["valve", "gate valve", "globe valve", "ball valve", "check valve", "butterfly valve"],
    "FITTING":    ["fitting", "elbow", "tee", "reducer", "coupling", "union", "nipple", "flange"],
    "FASTENER":   ["bolt", "nut", "washer", "stud", "screw", "rivet", "anchor"],
    "ELECTRICAL": ["cable", "wire", "transformer", "switchgear", "panel", "motor", "breaker"],
    "INSTRUMENT": ["gauge", "sensor", "transmitter", "indicator", "thermocouple", "flowmeter"],
    "GASKET":     ["gasket", "seal", "o-ring", "packing", "gland"],
    "PAINT":      ["paint", "primer", "coating", "epoxy", "lacquer", "varnish"],
    "CHEMICAL":   ["chemical", "acid", "solvent", "lubricant", "grease", "oil", "additive"],
    "BEARING":    ["bearing", "bush", "bushing", "roller", "ball bearing"],
    "PUMP":       ["pump", "centrifugal", "reciprocating", "submersible", "booster"],
    "CIVIL":      ["cement", "concrete", "brick", "sand", "aggregate", "rebar"],
    "SAFETY":     ["helmet", "glove", "goggle", "mask", "safety", "fire extinguisher", "ppe"],
    "GENERAL":    [],
}


def detect_category(text: str) -> str:
    """Detect material category from description text."""
    if not text:
        return "GENERAL"
    text_lower = text.lower()
    best_cat = "GENERAL"
    best_count = 0

    for category, keywords in _CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_cat = category

    return best_cat


# ── Sequence Counter (in-memory per session) ─────────────────────────
_sequence_counters: dict[str, int] = {}


def _next_seq(category: str) -> int:
    """Get next sequence number for a category."""
    if category not in _sequence_counters:
        _sequence_counters[category] = CNMC_START_SEQ
    seq = _sequence_counters[category]
    _sequence_counters[category] = seq + 1
    return seq


def generate_cnmc(descriptions: list[str]) -> str:
    """
    Generate a Common National Material Code for a cluster of descriptions.

    Format: CNMC-{CATEGORY}-{HASH}
    Example: CNMC-STEEL-A8F3B9
    """
    combined = " ".join(sorted(descriptions))
    category = detect_category(combined)
    hash_str = hashlib.md5(combined.encode('utf-8')).hexdigest()[:6].upper()
    return f"{CNMC_PREFIX}-{category}-{hash_str}"


def generate_cnmc_for_clusters(
    clusters: list[list[int]],
    descriptions: list[str],
) -> list[dict]:
    """
    Assign CNMC codes to each cluster.

    Returns list of:
    {
        "cnmc_code": "CNMC-STEEL-2001",
        "category": "STEEL",
        "member_indices": [0, 3, 7],
        "member_descriptions": ["...", "...", "..."]
    }
    """
    results = []
    for cluster_indices in clusters:
        cluster_descs = [descriptions[i] for i in cluster_indices]
        combined = " ".join(sorted(cluster_descs))
        category = detect_category(combined)
        
        # Deterministic hash prevents duplicate clusters on multiple runs
        hash_str = hashlib.md5(combined.encode('utf-8')).hexdigest()[:6].upper()
        code = f"{CNMC_PREFIX}-{category}-{hash_str}"

        results.append({
            "cnmc_code": code,
            "category": category,
            "member_indices": cluster_indices,
            "member_descriptions": cluster_descs,
        })

    return results


def reset_sequences():
    """Reset all sequence counters (useful for testing)."""
    global _sequence_counters
    _sequence_counters = {}
