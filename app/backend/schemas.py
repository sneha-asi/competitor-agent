"""JSON schemas for each agent's structured output.

These feed Claude's `output_config.format` (json_schema), so they obey the structured-output
rules: every object sets additionalProperties:false, and we use ARRAYS instead of dynamic-keyed
objects (open `additionalProperties` schemas aren't supported). The matrix therefore carries
`verdicts` as a list of {platform,status,...}; pipeline.py converts that to the renderer's
name-keyed object before assembling data.json.
"""

STATUS_ENUM = ["owned", "ahead", "partial", "gap", "unknown"]


def _obj(props, required):
    return {"type": "object", "additionalProperties": False, "properties": props, "required": required}


def _arr(items):
    return {"type": "array", "items": items}


_str = {"type": "string"}
_strs = _arr(_str)

# ---- Phase A ----
PROFILE_PART = _obj({
    "capabilities": _strs,
    "category": _str, "icp": _str, "positioning": _str,
    "signals": _strs, "notes": _str,
}, ["capabilities"])

_footprint = _arr(_obj({"label": _str, "value": _str}, ["label", "value"]))

PRODUCT_PROFILE = _obj({
    "name": _str, "category": _str, "icp": _str, "what_it_is": _str, "positioning": _str,
    "signature": _str, "money_question": _str,
    "capabilities": _strs, "footprint": _footprint, "search_seeds": _strs,
}, ["name", "category", "capabilities", "search_seeds"])

# ---- Phase B ----
CANDIDATE_LIST = _obj({
    "candidates": _arr(_obj({
        "name": _str, "url": _str, "why": _str,
        "leadership_signals": _strs, "sources": _strs,
    }, ["name", "why"])),
}, ["candidates"])

RANKED = _obj({
    "ranked": _arr(_obj({
        "name": _str, "url": _str, "why": _str,
        "leadership_score": {"type": "number"},
        "leadership_signals": _strs, "sources": _strs,
    }, ["name", "why", "leadership_score"])),
    "top2": _arr(_obj({"name": _str, "url": _str, "why": _str}, ["name", "why"])),
}, ["ranked", "top2"])

# ---- Phase C ----
FINDINGS = _obj({
    "dimension": _str,
    "findings": _arr(_obj({
        "claim": _str, "detail": _str, "source": _str, "date": _str,
        "tier": {"type": "string", "enum": ["primary", "aggregator", "review", "blog"]},
    }, ["claim", "source"])),
    "unknowns": _strs,
}, ["dimension", "findings"])

COMPETITOR_PROFILE = _obj({
    "name": _str, "url": _str, "what_it_is": _str, "category_label": _str,
    "money_question": _str, "signature": _str, "footprint": _footprint,
    "capabilities": _arr(_obj({"name": _str, "status_hint": _str, "source": _str}, ["name"])),
    "gaps": _strs,
    "sources": _arr(_obj({"label": _str, "url": _str}, ["label", "url"])),
}, ["name", "what_it_is", "capabilities", "sources"])

# ---- Phase D ----
MATRIX = _obj({
    "capabilities": _arr(_obj({
        "name": _str, "reality": _str,
        "verdicts": _arr(_obj({
            "platform": _str,
            "status": {"type": "string", "enum": STATUS_ENUM},
            "note": _str, "source": _str,
        }, ["platform", "status"])),
    }, ["name", "reality", "verdicts"])),
    "glance_notes": _arr(_obj({"count": _str, "title": _str, "body": _str}, ["title"])),
}, ["capabilities"])

_chip = _obj({"tone": _str, "icon": _str, "title": _str, "body": _str}, ["tone", "title", "body"])
_titled = _obj({"title": _str, "body": _str}, ["title", "body"])
_checklist = _obj({"title": _str, "tone": _str, "marker": _str, "marker_color": _str, "items": _strs}, ["title", "items"])

NARRATIVE = _obj({
    "hero": _obj({"kicker": _str, "tagline": _str, "subtitle": _str}, ["tagline"]),
    "tldr": _obj({"lead_in": _str, "sub": _str, "paragraphs": _strs, "chips": _arr(_chip)}, ["sub", "paragraphs"]),
    "ahead": _obj({"sub": _str, "items": _arr(_titled)}, ["items"]),
    "closeable": _obj({"sub": _str, "items": _arr(_obj({
        "title": _str, "desc": _str, "effort": _str,
        "priority": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
        "effort_level": {"type": "string", "enum": ["low", "med", "high"]},
        "value": {"type": "string", "enum": ["low", "med", "high"]},
    }, ["title"]))}, ["items"]),
    "decisions": _obj({"sub": _str, "items": _arr(_titled)}, ["items"]),
    "positioning": _obj({
        "sub": _str,
        "stats": _arr(_obj({"tone": _str, "value": _str, "label": _str}, ["value", "label"])),
        "paragraphs": _strs, "pullquote": _str, "closing": _str,
        "checklists": _arr(_checklist),
    }, ["paragraphs"]),
}, ["hero", "tldr", "ahead", "closeable", "decisions", "positioning"])

# ---- Phase E ----
REFUTE = _obj({
    "supported": {"type": "boolean"},
    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    "reason": _str,
}, ["supported", "reason"])
