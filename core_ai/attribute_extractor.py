"""
attribute_extractor.py — Regex/NER Spec Extractor
Extracts structured technical attributes (size, material grade, pressure, etc.)
from free-text material descriptions.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ExtractedAttributes:
    """Container for extracted technical attributes."""
    size: str = ""
    material: str = ""
    grade: str = ""
    pressure_rating: str = ""
    schedule: str = ""
    standard: str = ""
    form: str = ""
    end_type: str = ""
    extras: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "size": self.size,
            "material": self.material,
            "grade": self.grade,
            "pressure_rating": self.pressure_rating,
            "schedule": self.schedule,
            "standard": self.standard,
            "form": self.form,
            "end_type": self.end_type,
        }
        d.update(self.extras)
        return {k: v for k, v in d.items() if v}

    def to_string(self) -> str:
        """Flatten attributes to a comparable string for scoring."""
        parts = [v for v in self.to_dict().values() if v]
        return " ".join(str(p) for p in parts).lower()


# ── Regex Pattern Library ─────────────────────────────────────────────

# Size patterns: "2 inch", "50mm", "DN50", "1/2 inch", "3/4\"", "NB 25"
_SIZE_PATTERNS = [
    r"(\d+(?:\.\d+)?(?:\s*/\s*\d+)?)\s*(?:inch|in|\"|\u2033)",
    r"(\d+(?:\.\d+)?)\s*(?:mm|millimeter|millimetre)",
    r"(?:dn|nb|nps)\s*(\d+(?:\.\d+)?)",
    r"(\d+(?:\.\d+)?)\s*(?:meter|metre|mtr|m)\b",
    r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(?:mm|inch|in)?",
]

# Material patterns
_MATERIAL_PATTERNS = [
    r"\b(stainless\s+steel|carbon\s+steel|mild\s+steel|cast\s+(?:iron|steel))\b",
    r"\b(galvanized\s+iron|wrought\s+iron|ductile\s+iron)\b",
    r"\b(aluminium|aluminum|copper|brass|bronze|nickel|titanium|inconel|monel)\b",
    r"\b(polyvinyl\s+chloride|high\s+density\s+polyethylene|polypropylene)\b",
    r"\b(rubber|neoprene|viton|ptfe|teflon|nylon|fiber\s+reinforced\s+plastic)\b",
    r"\b(ss\s*\d{3}[a-z]?)\b",
    r"\b(a\s*\d{3}\s*(?:gr(?:ade)?\.?\s*[a-z0-9]+)?)\b",
]

# Grade patterns
_GRADE_PATTERNS = [
    r"\b(?:grade|gr\.?)\s*([a-z0-9]+(?:\s*[a-z0-9])?)\b",
    r"\b(?:class|cl\.?)\s*(\d+)\b",
    r"\b(is\s*\d{3,5})\b",
    r"\b(astm\s*[a-z]?\s*\d{2,5})\b",
    r"\b(api\s*\d{1,2}[a-z]?)\b",
    r"\b(din\s*\d{3,5})\b",
    r"\b(ansi\s*[a-z]?\s*\d+\.?\d*)\b",
    r"\b(asme\s*[a-z]?\s*\d+\.?\d*)\b",
]

# Pressure / rating patterns
_PRESSURE_PATTERNS = [
    r"(\d+)\s*(?:psi|bar|mpa|kpa)\b",
    r"(\d+)\s*(?:#|lb|pound)\b",
    r"(?:pressure|rating)\s*[:=]?\s*(\d+(?:\.\d+)?)",
    r"\b(\d{3,4})\s*(?:wog|cwp)\b",
]

# Schedule patterns
_SCHEDULE_PATTERNS = [
    r"\b(?:schedule|sch\.?)\s*(xs|xxs|std|10s?|20s?|40s?|60|80s?|100|120|140|160)\b",
]

# Form / shape patterns
_FORM_PATTERNS = [
    r"\b(pipe|tube|plate|sheet|bar|rod|angle|channel|beam|coil|strip|wire)\b",
    r"\b(elbow|tee|reducer|coupling|union|nipple|cap|plug|bushing)\b",
    r"\b(flange|gasket|bolt|nut|washer|stud|valve|check\s+valve|gate\s+valve|globe\s+valve|ball\s+valve)\b",
]

# End connection patterns
_END_PATTERNS = [
    r"\b(socket\s+weld|butt\s+weld|threaded|flanged|screwed|grooved|compression)\b",
    r"\b(raised\s+face|flat\s+face|ring\s+type\s+joint|male|female)\b",
]


def _search_first(patterns: list[str], text: str) -> str:
    """Return the first match from a list of regex patterns."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return ""


def extract_attributes(text: str) -> ExtractedAttributes:
    """
    Extract structured technical attributes from a material description.
    Works on the raw (or lightly cleaned) text.
    """
    if not text or not isinstance(text, str):
        return ExtractedAttributes()

    t = text.lower()

    attrs = ExtractedAttributes(
        size=_search_first(_SIZE_PATTERNS, t),
        material=_search_first(_MATERIAL_PATTERNS, t),
        grade=_search_first(_GRADE_PATTERNS, t),
        pressure_rating=_search_first(_PRESSURE_PATTERNS, t),
        schedule=_search_first(_SCHEDULE_PATTERNS, t),
        form=_search_first(_FORM_PATTERNS, t),
        end_type=_search_first(_END_PATTERNS, t),
    )

    # Build standard reference from grade if not explicit
    if not attrs.standard and attrs.grade:
        std_match = re.search(r"\b(is|astm|api|din|ansi|asme)\b", attrs.grade, re.IGNORECASE)
        if std_match:
            attrs.standard = std_match.group(0)

    return attrs


def extract_attributes_batch(texts: list[str]) -> list[dict]:
    """Extract attributes for a batch of descriptions; returns list of dicts."""
    return [extract_attributes(t).to_dict() for t in texts]
