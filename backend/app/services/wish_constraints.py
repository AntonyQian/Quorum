"""Deterministic Wish constraints merged with the model's parsed fields (SPEC §6)."""

import re

_BUDGET = re.compile(
    r"(?:under|below|less than|max(?:imum)?|up to|<)\s*\$?\s*(\d+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
_DOLLAR = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")

_CATEGORY_PHRASES: tuple[tuple[str, str], ...] = (
    ("dining table", "dining_table"),
    ("coffee table", "seating"),
    ("side table", "seating"),
    ("table", "dining_table"),
    ("bookshelf", "bookshelf"),
    ("bookcase", "bookshelf"),
    ("sofa", "sofa"),
    ("couch", "sofa"),
    ("chair", "chair"),
    ("desk", "desk"),
    ("bed", "bedroom"),
    ("bedroom", "bedroom"),
    ("lamp", "lighting"),
    ("lighting", "lighting"),
    ("storage", "storage"),
    ("bench", "seating"),
    ("seating", "seating"),
)


def budget_max_cents_from_text(text: str) -> int | None:
    """Parse shopper budget from phrases like ``under 50``, ``under $200``, ``max $1,200``."""
    for pattern in (_BUDGET, _DOLLAR):
        match = pattern.search(text)
        if match:
            dollars = float(match.group(1).replace(",", ""))
            if dollars > 0:
                return int(round(dollars * 100))
    return None


def category_from_text(text: str) -> str | None:
    lowered = text.lower()
    for phrase, category in _CATEGORY_PHRASES:
        if phrase in lowered:
            return category
    return None


def merge_parsed_fields(text: str, parsed: dict) -> dict:
    """Prefer the tightest budget and fill gaps the model missed."""
    from_text_budget = budget_max_cents_from_text(text)
    from_text_category = category_from_text(text)

    budget = parsed.get("budget_max_cents")
    if from_text_budget is not None:
        budget = from_text_budget if budget is None else min(budget, from_text_budget)

    category = parsed.get("category") or from_text_category

    return {
        "category": category,
        "budget_max_cents": budget,
        "style_tags": parsed.get("style_tags") or [],
        "size_notes": parsed.get("size_notes"),
    }
