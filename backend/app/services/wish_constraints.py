"""Deterministic Wish constraints merged with the model's parsed fields (SPEC §6)."""

import re
from typing import Protocol

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

_STYLE_TOKENS: tuple[str, ...] = (
    "walnut",
    "oak",
    "maple",
    "birch",
    "teak",
    "ash",
    "pine",
    "linen",
    "leather",
    "brass",
    "marble",
    "mid-century",
    "farmhouse",
    "minimal",
    "industrial",
    "scandinavian",
)


def normalize_wish_text(text: str) -> str:
    """Lowercase and fix common typos so category/style parsing stays stable."""
    return text.lower().replace("dinning", "dining")


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
    lowered = normalize_wish_text(text)
    for phrase, category in _CATEGORY_PHRASES:
        if phrase in lowered:
            return category
    return None


def style_tags_from_text(text: str) -> list[str]:
    lowered = normalize_wish_text(text)
    return [token for token in _STYLE_TOKENS if token in lowered]


class _HiddenProductLike(Protocol):
    category: str
    name: str
    style_tags: list[str] | None


def hidden_product_fit_score(text: str, parsed: dict, product: _HiddenProductLike) -> int:
    """Score a hidden listing against merged Wish fields (used for Demand Hits when the model omits matches)."""
    category = parsed.get("category")
    if category is not None and product.category != category:
        return 0

    score = 50 if category is not None else 25
    wish_tags = set(parsed.get("style_tags") or []) | set(style_tags_from_text(text))
    product_tags = {t.lower() for t in (product.style_tags or [])}
    name_lower = product.name.lower()

    if wish_tags:
        if wish_tags & product_tags or any(tag in name_lower for tag in wish_tags):
            score += 40
    else:
        stop = {"a", "an", "the", "for", "and", "or", "to", "table", "dining", "set", "want", "need", "looking"}
        wish_words = set(re.findall(r"[a-z]+", normalize_wish_text(text))) - stop
        name_words = set(re.findall(r"[a-z]+", name_lower))
        if wish_words & name_words:
            score += 25

    return min(100, score)


def merge_parsed_fields(text: str, parsed: dict) -> dict:
    """Prefer the tightest budget and fill gaps the model missed."""
    from_text_budget = budget_max_cents_from_text(text)
    from_text_category = category_from_text(text)

    budget = parsed.get("budget_max_cents")
    if from_text_budget is not None:
        budget = from_text_budget if budget is None else min(budget, from_text_budget)

    category = parsed.get("category") or from_text_category

    llm_tags = [str(t).lower() for t in (parsed.get("style_tags") or [])]
    text_tags = style_tags_from_text(text)
    style_tags = list(dict.fromkeys([*llm_tags, *text_tags]))

    return {
        "category": category,
        "budget_max_cents": budget,
        "style_tags": style_tags,
        "size_notes": parsed.get("size_notes"),
    }
