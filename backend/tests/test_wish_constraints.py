"""Deterministic Wish constraint parsing."""

from app.services.wish_constraints import (
    budget_max_cents_from_text,
    categories_compatible,
    category_from_text,
    merge_parsed_fields,
    style_tags_from_text,
)


def test_budget_from_under_without_dollar_sign():
    assert budget_max_cents_from_text("table under 50") == 5_000


def test_budget_from_under_with_dollar_sign():
    assert budget_max_cents_from_text("chair under $200") == 20_000


def test_a_plain_table_covers_every_kind_of_table_but_a_coffee_table_does_not():
    assert category_from_text("table under 50") == "any_table"
    assert categories_compatible("any_table", "dining_table") and categories_compatible("any_table", "table")
    assert not categories_compatible("table", "dining_table")
    assert not categories_compatible("dining_table", "table")


def test_dinning_typo_still_maps_to_dining_table_and_walnut():
    assert category_from_text("walnut dinning table") == "dining_table"
    assert style_tags_from_text("walnut dinning table") == ["walnut"]


def test_merge_tightens_llm_budget_and_fills_missing():
    merged = merge_parsed_fields(
        "table under 50",
        {"category": "dining_table", "budget_max_cents": None, "style_tags": [], "size_notes": None},
    )
    assert merged["budget_max_cents"] == 5_000
    assert merged["category"] == "any_table"


def test_chair_and_side_table_map_to_catalog_categories():
    assert category_from_text("a chair") == "seating"
    assert category_from_text("walnut side table") == "table"
    assert category_from_text("coffee table") == "table"


def test_the_literal_word_null_from_the_model_is_not_a_category():
    merged = merge_parsed_fields("walnut", {"category": "null", "style_tags": ["walnut"]})
    assert merged["category"] is None


def test_a_material_alone_does_not_inherit_a_category_the_model_guessed():
    merged = merge_parsed_fields("teak", {"category": "seating", "style_tags": ["teak"]})
    assert merged["category"] is None
    assert merge_parsed_fields("teak chair", {"category": "seating"})["category"] == "seating"


def test_required_terms_match_whole_words_only():
    from app.services.wish_constraints import product_has_terms, required_terms

    assert required_terms("wash cloth") == []
    assert required_terms("Gray sofa in WALNUT") == ["walnut", "grey"]
    wash = type("P", (), {"name": "Washstand", "description": "", "style_tags": []})()
    ash = type("P", (), {"name": "White Ash Shelf", "description": "", "style_tags": []})()
    assert not product_has_terms(wash, ["ash"])
    assert product_has_terms(ash, ["ash"])


def test_categories_match_whole_words_so_adjustable_is_not_a_table():
    assert category_from_text("height-adjustable desk") == "desk"
    assert category_from_text("two chairs") == "seating"
    assert category_from_text("tables") == "any_table"


def test_the_shoppers_own_category_word_beats_the_models_guess():
    assert merge_parsed_fields("coffee table", {"category": "dining_table"})["category"] == "table"
