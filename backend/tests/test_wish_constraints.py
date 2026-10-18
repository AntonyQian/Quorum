"""Deterministic Wish constraint parsing."""

from app.services.wish_constraints import (
    budget_max_cents_from_text,
    category_from_text,
    merge_parsed_fields,
    style_tags_from_text,
)


def test_budget_from_under_without_dollar_sign():
    assert budget_max_cents_from_text("table under 50") == 5_000


def test_budget_from_under_with_dollar_sign():
    assert budget_max_cents_from_text("chair under $200") == 20_000


def test_category_table_maps_to_dining_table():
    assert category_from_text("table under 50") == "dining_table"


def test_dinning_typo_still_maps_to_dining_table_and_walnut():
    assert category_from_text("walnut dinning table") == "dining_table"
    assert style_tags_from_text("walnut dinning table") == ["walnut"]


def test_merge_tightens_llm_budget_and_fills_missing():
    merged = merge_parsed_fields(
        "table under 50",
        {"category": "dining_table", "budget_max_cents": None, "style_tags": [], "size_notes": None},
    )
    assert merged["budget_max_cents"] == 5_000
    assert merged["category"] == "dining_table"
