"""
Application Configuration — National Unified Material Master Platform
All paths, thresholds, and system parameters.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ── Upload & Storage ──────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "txt"}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB

# ── AI Matching Thresholds ────────────────────────────────────────────
MATCH_THRESHOLD = 0.65          # 65% — items at or above are auto-clustered
HIGH_CONFIDENCE = 0.92          # 92% — auto-approve candidate
LOW_CONFIDENCE  = 0.60          # below this — no suggestion shown

# ── Composite Score Weights ───────────────────────────────────────────
WEIGHT_SEMANTIC   = 0.50
WEIGHT_ATTRIBUTE  = 0.40
WEIGHT_FUZZY      = 0.10

# ── Vectorizer Settings ──────────────────────────────────────────────
TFIDF_MAX_FEATURES = 10_000
TFIDF_NGRAM_RANGE  = (1, 3)
EMBEDDING_MODEL    = "all-MiniLM-L6-v2"   # lightweight, fast

# ── CNMC Code Prefix ─────────────────────────────────────────────────
CNMC_PREFIX = "CNMC"
CNMC_START_SEQ = 2001

# ── Standard Schema Fields ────────────────────────────────────────────
STANDARD_FIELDS = [
    "cpse_name",
    "local_material_code",
    "material_description",
    "technical_specs",
    "unit_of_measure",
    "stock_quantity",
]

# ── Fuzzy Column Mapping Keywords ─────────────────────────────────────
COLUMN_KEYWORD_MAP = {
    "cpse_name": [
        "cpse", "company", "enterprise", "org", "organisation", "organization",
        "psu", "entity", "corp", "undertaking", "firm",
    ],
    "local_material_code": [
        "mat_code", "material_code", "local_code", "item_code", "part_no",
        "part_number", "sku", "stock_code", "sap_code", "erp_code", "code",
    ],
    "material_description": [
        "mat_desc", "material_desc", "description", "item_desc", "item_details",
        "item_name", "material_name", "part_desc", "name", "details",
    ],
    "technical_specs": [
        "spec", "specs", "specification", "specifications", "tech_spec",
        "technical", "spec_text", "parameters", "attributes", "grade",
    ],
    "unit_of_measure": [
        "uom", "unit", "unit_of_measure", "measure", "measurement",
        "qty_unit", "unit_type",
    ],
    "stock_quantity": [
        "qty", "quantity", "stock", "stock_qty", "available_qty", "on_hand",
        "balance", "inventory", "count",
    ],
}

# ── Domain Abbreviation Map (used in preprocessor) ────────────────────
DOMAIN_ABBREVIATIONS = {
    "stl":   "steel",
    "ss":    "stainless steel",
    "cs":    "carbon steel",
    "ms":    "mild steel",
    "gi":    "galvanized iron",
    "ci":    "cast iron",
    "al":    "aluminium",
    "cu":    "copper",
    "br":    "brass",
    "sch":   "schedule",
    "dia":   "diameter",
    "thk":   "thick",
    "lg":    "long",
    "od":    "outer diameter",
    "id":    "inner diameter",
    "nb":    "nominal bore",
    "nps":   "nominal pipe size",
    "psi":   "pounds per square inch",
    "mpa":   "megapascal",
    "hp":    "horsepower",
    "kw":    "kilowatt",
    "rpm":   "revolutions per minute",
    "sqm":   "square meter",
    "sqft":  "square feet",
    "rmt":   "running meter",
    "mtr":   "meter",
    "mm":    "millimeter",
    "kg":    "kilogram",
    "mt":    "metric ton",
    "nos":   "numbers",
    "pcs":   "pieces",
    "ea":    "each",
    "set":   "set",
    "ltr":   "liter",
    "gal":   "gallon",
    "pvc":   "polyvinyl chloride",
    "hdpe":  "high density polyethylene",
    "pp":    "polypropylene",
    "ptfe":  "polytetrafluoroethylene",
    "grp":   "glass reinforced plastic",
    "frp":   "fiber reinforced plastic",
    "erw":   "electric resistance welded",
    "smls":  "seamless",
    "rf":    "raised face",
    "ff":    "flat face",
    "sw":    "socket weld",
    "bw":    "butt weld",
    "thd":   "threaded",
    "flg":   "flange",
    "bsp":   "british standard pipe",
    "npt":   "national pipe thread",
    "astm":  "astm",
    "is":    "indian standard",
    "din":   "din",
    "api":   "api",
    "ansi":  "ansi",
    "asme":  "asme",
    "gr":    "grade",
    "flgd":  "flange",
    "wtr":   "water",
    "ph":    "phase",
    "sqmm":  "square millimeter",
    "conn":  "connection",
    "pcs":   "pieces",
    "mtrs":  "meter",
    "cl":    "class",
    "horiz": "horizontal",
    "galv":  "galvanized",
    "eq":    "equal",
    "hi":    "high"
}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
