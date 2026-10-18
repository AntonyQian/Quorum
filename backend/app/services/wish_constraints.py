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
    ("dining set", "dining_table"),
    ("coffee table", "table"),
    ("side table", "table"),
    ("end table", "table"),
    ("table", "any_table"),
    ("bookshelf", "bookshelf"),
    ("bookcase", "bookshelf"),
    ("sofa", "sofa"),
    ("couch", "sofa"),
    ("armchair", "seating"),
    ("chair", "seating"),
    ("loveseat", "sofa"),
    ("shelf", "bookshelf"),
    ("shelves", "bookshelf"),
    ("shelving", "bookshelf"),
    ("nightstand", "bedroom"),
    ("wardrobe", "bedroom"),
    ("sideboard", "storage"),
    ("console", "storage"),
    ("cabinet", "storage"),
    ("tv stand", "storage"),
    ("desk", "desk"),
    ("bed", "bedroom"),
    ("bedroom", "bedroom"),
    ("lamp", "lighting"),
    ("lighting", "lighting"),
    ("storage", "storage"),
    ("bench", "seating"),
    ("seating", "seating"),
)

# Materials and colors a shopper names on purpose: a Pool must actually have them to be shown.
_MATERIAL_TOKENS: tuple[str, ...] = (
    "walnut",
    "oak",
    "maple",
    "birch",
    "teak",
    "ash",
    "pine",
    "cedar",
    "linen",
    "leather",
    "velvet",
    "boucle",
    "brass",
    "steel",
    "marble",
    "black",
    "white",
    "grey",
    "green",
    "tan",
    "cream",
    "brown",
    "mustard",
    "cognac",
)

_STYLE_TOKENS: tuple[str, ...] = _MATERIAL_TOKENS + (
    "mid-century",
    "farmhouse",
    "minimal",
    "industrial",
    "scandinavian",
)


_NO_CATEGORY = {"", "null", "none", "n/a", "unknown", "unclear", "any"}


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
    """The category the shopper's own words name, matched as whole words (plurals allowed), so "adjustable desk"
    is a desk, not a table."""
    lowered = normalize_wish_text(text)
    for phrase, category in _CATEGORY_PHRASES:
        if re.search(rf"(?<![a-z]){re.escape(phrase)}(?:s|es)?(?![a-z])", lowered):
            return category
    return None


def _has_word(haystack: str, word: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", haystack) is not None


def style_tags_from_text(text: str) -> list[str]:
    lowered = normalize_wish_text(text).replace("gray", "grey").replace("bouclé", "boucle")
    return [token for token in _STYLE_TOKENS if _has_word(lowered, token)]


def required_terms(text: str) -> list[str]:
    """Materials and colors the shopper's own words name; every shown Pool must carry them."""
    named = set(style_tags_from_text(text))
    return [t for t in _MATERIAL_TOKENS if t in named]


class _PoolProductLike(Protocol):
    name: str
    description: str
    style_tags: list[str] | None


def product_has_terms(product: _PoolProductLike, terms: list[str]) -> bool:
    """True when the Product's name, tags, or description mentions every required material or color."""
    haystack = " ".join([product.name, product.description or "", *(product.style_tags or [])]).lower()
    haystack = haystack.replace("bouclé", "boucle").replace("gray", "grey")
    return all(_has_word(haystack, term) for term in terms)


# Wish categories broader than any one Product category: a plain "table" covers dining and coffee tables, but a
# "coffee table" Wish does not cover dining tables.
_CATEGORY_FAMILIES = {"any_table": {"table", "dining_table"}}


def categories_compatible(wanted: str, actual: str) -> bool:
    """True when a Product in `actual` fits a Wish for `wanted`."""
    return actual in _CATEGORY_FAMILIES.get(wanted, {wanted})


class _HiddenProductLike(Protocol):
    category: str
    name: str
    style_tags: list[str] | None


def hidden_product_fit_score(text: str, parsed: dict, product: _HiddenProductLike) -> int:
    """Score a hidden listing against merged Wish fields (used for Demand Hits when the model omits matches)."""
    category = parsed.get("category")
    if category is not None and not categories_compatible(category, product.category):
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
    """Prefer the tightest budget, let the shopper's own category word beat the model's guess, and fill gaps the
    model missed."""
    from_text_budget = budget_max_cents_from_text(text)
    from_text_category = category_from_text(text)

    budget = parsed.get("budget_max_cents")
    if from_text_budget is not None:
        budget = from_text_budget if budget is None else min(budget, from_text_budget)

    llm_category = str(parsed.get("category") or "").strip().lower().replace(" ", "_")
    category = from_text_category or (llm_category if llm_category not in _NO_CATEGORY else None)
    if from_text_category is None and required_terms(text):
        category = None  # "teak" names a material, not a category the model should guess

    llm_tags = [str(t).lower() for t in (parsed.get("style_tags") or [])]
    text_tags = style_tags_from_text(text)
    style_tags = list(dict.fromkeys([*llm_tags, *text_tags]))

    return {
        "category": category,
        "budget_max_cents": budget,
        "style_tags": style_tags,
        "size_notes": parsed.get("size_notes"),
    }
