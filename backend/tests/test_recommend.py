"""Ticket #25: POST /api/recommend. One LLM call parses the Wish; code picks which live Pools are shown (SPEC §6, §8).

The LLM call is stubbed at `recommender.complete` (prompt in, structured output out), so no test touches
the network.
"""

from datetime import timedelta
from types import SimpleNamespace

import httpx
import openai
import pytest
from sqlmodel import select

from app.models import Pool, Product, Retailer, Tier, User, Wish
from app.services import recommender
from app.services.recommender import RecommenderError, RecommenderOutput

from tests.conftest import T0, as_user, assert_error

SUMMARY_KEYS = {
    "id", "product", "status", "participants", "tiers", "current_price_cents",
    "next_tier", "deadline", "time_left_seconds", "stock_cap",
}
PARSED = {"category": "dining_table", "budget_max_cents": 80000, "style_tags": ["walnut"],
          "size_notes": "seats 4"}


@pytest.fixture
def world(session):
    oak = Retailer(name="Oak & Co.")
    session.add(oak)
    session.commit()
    alice = User(name="Alice", role="shopper")
    session.add(alice)

    def product(name, category, visibility="public"):
        p = Product(retailer_id=oak.id, name=name, category=category, style_tags=["walnut"],
                    list_price_cents=80_000, floor_price_cents=50_000, visibility=visibility, created_at=T0)
        session.add(p)
        session.commit()
        return p

    def pool(prod, status="open"):
        p = Pool(product_id=prod.id, status=status, opened_at=T0, deadline=T0 + timedelta(days=2))
        session.add(p)
        session.commit()
        session.add(Tier(pool_id=p.id, ordinal=1, min_participants=3, discount_cents=10_000))
        session.commit()
        return p

    table = pool(product("Walnut Table", "dining_table"))
    sofa = pool(product("Walnut Sofa", "sofa"))
    lamp = pool(product("Brass Lamp", "lamp"), status="locked")
    done = pool(product("Old Chair", "chair"), status="completed")
    hidden = product("Secret Desk", "desk", visibility="hidden")
    session.commit()
    return dict(alice=alice, table=table, sofa=sofa, lamp=lamp, done=done, hidden=hidden)


@pytest.fixture
def claude(monkeypatch):
    """Stub the LLM call: records each prompt and returns `claude.output` (or raises `claude.error`)."""

    class Stub:
        output = {"parsed": PARSED, "pool_matches": [], "hidden_matches": []}
        error = None
        prompts: list[str] = []

        def __call__(self, prompt):
            self.prompts.append(prompt)
            if self.error:
                raise self.error
            return RecommenderOutput.model_validate(self.output)

    stub = Stub()
    stub.prompts = []
    monkeypatch.setattr(recommender, "complete", stub)
    return stub


def test_recommend_returns_wish_id_parsed_and_pool_summaries(client, world, claude):
    claude.output = {
        "parsed": PARSED,
        "pool_matches": [
            {"pool_id": world["sofa"].id, "fit_score": 60},
            {"pool_id": world["table"].id, "fit_score": 91},
        ],
        "hidden_matches": [],
    }

    r = client.post("/api/recommend", json={"text": "walnut dining table for 4"}, headers=as_user(world["alice"]))

    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"wish_id", "parsed", "recommendations", "suggestions"}
    assert isinstance(body["wish_id"], int)
    assert body["parsed"] == PARSED
    assert [rec["pool"]["id"] for rec in body["recommendations"]] == [world["table"].id]
    assert body["suggestions"] == []  # the model's sofa pick is not a dining table, so it is not shown
    first = body["recommendations"][0]
    assert set(first) == {"pool"}
    assert set(first["pool"]) == SUMMARY_KEYS


def test_a_table_wish_shows_every_live_table_pool_whatever_the_model_picks(client, session, world, claude):
    retailer_id = session.get(Product, world["table"].product_id).retailer_id
    extra = [_add_pool(session, retailer_id, f"Table {i}", "dining_table", []).id for i in range(6)]
    claude.output = {
        "parsed": {"category": None, "style_tags": []},
        "pool_matches": [
            {"pool_id": world["sofa"].id, "fit_score": 99},
            {"pool_id": world["done"].id, "fit_score": 99},
            {"pool_id": 9999, "fit_score": 98},
            {"pool_id": extra[0], "fit_score": 61},
        ],
        "hidden_matches": [],
    }

    r = client.post("/api/recommend", json={"text": "table"}, headers=as_user(world["alice"]))

    assert r.status_code == 200, r.text
    assert [rec["pool"]["id"] for rec in r.json()["recommendations"]] == [world["table"].id, *extra]  # by deadline
    assert r.json()["suggestions"] == []


def test_the_same_wish_shows_the_same_pools_however_the_model_answers(client, session, world, claude):
    retailer_id = session.get(Product, world["table"].product_id).retailer_id
    coffee = _add_pool(session, retailer_id, "Low Coffee Table", "table", ["oak"])
    outputs = [
        {"parsed": {"category": "dining_table"}, "pool_matches": [], "hidden_matches": []},
        {"parsed": {"category": "sofa"}, "pool_matches": [{"pool_id": world["sofa"].id, "fit_score": 95}],
         "hidden_matches": []},
        {"parsed": {}, "pool_matches": [{"pool_id": coffee.id, "fit_score": 70}], "hidden_matches": []},
    ]
    results = []
    for output in outputs:
        claude.output = output
        r = client.post("/api/recommend", json={"text": "table"}, headers=as_user(world["alice"]))
        results.append([rec["pool"]["id"] for rec in r.json()["recommendations"]])
    assert results == [[world["table"].id, coffee.id]] * 3


def test_prompt_includes_the_wish_and_live_public_pools_only(client, world, claude):
    client.post("/api/recommend", json={"text": "walnut dining table for 4"}, headers=as_user(world["alice"]))

    [prompt] = claude.prompts
    assert "walnut dining table for 4" in prompt
    for name in ("Walnut Table", "Walnut Sofa", "Brass Lamp"):
        assert name in prompt
    assert "Old Chair" not in prompt  # completed Pool
    public_section = prompt.split("<public_pools>")[1].split("</public_pools>")[0]
    assert "Secret Desk" not in public_section  # Hidden Listings go in their own section (ticket #26)


def test_a_live_pool_on_a_hidden_product_is_never_a_public_candidate(client, session, world, claude):
    bench = Product(retailer_id=world["hidden"].retailer_id, name="Hidden Bench", category="bench",
                    list_price_cents=80_000, floor_price_cents=50_000, visibility="hidden", created_at=T0)
    session.add(bench)
    session.commit()
    pool = Pool(product_id=bench.id, status="open", opened_at=T0, deadline=T0 + timedelta(days=2))
    session.add(pool)
    session.commit()
    session.add(Tier(pool_id=pool.id, ordinal=1, min_participants=3, discount_cents=10_000))
    session.commit()
    claude.output = {"parsed": {}, "pool_matches": [{"pool_id": pool.id, "fit_score": 99}], "hidden_matches": []}

    r = client.post("/api/recommend", json={"text": "something to sit on"}, headers=as_user(world["alice"]))
    assert r.status_code == 200, r.text
    assert r.json()["recommendations"] == []
    public_section = claude.prompts[0].split("<public_pools>")[1].split("</public_pools>")[0]
    assert "Hidden Bench" not in public_section


def test_a_category_we_do_not_sell_shows_nothing_rather_than_everything(client, world, claude):
    claude.output = {"parsed": PARSED, "pool_matches": [{"pool_id": world["table"].id, "fit_score": 90}],
                     "hidden_matches": []}

    r = client.post("/api/recommend", json={"text": "a bench"}, headers=as_user(world["alice"]))

    assert r.json()["parsed"]["category"] == "seating"
    assert r.json()["recommendations"] == r.json()["suggestions"] == []


def test_the_wish_is_saved_with_its_parsed_fields(client, session, world, claude):
    r = client.post("/api/recommend", json={"text": "walnut dining table for 4"}, headers=as_user(world["alice"]))

    wish = session.get(Wish, r.json()["wish_id"])
    assert wish.user_id == world["alice"].id
    assert wish.text == "walnut dining table for 4"
    assert wish.parsed == PARSED
    assert wish.created_at == T0  # Sim Clock


def test_table_under_50_over_budget_pool_is_only_a_suggestion(client, world, claude):
    claude.output = {
        "parsed": {"category": None, "budget_max_cents": None, "style_tags": [], "size_notes": None},
        "pool_matches": [{"pool_id": world["table"].id, "fit_score": 80}],
        "suggestions": [],
        "hidden_matches": [],
    }

    r = client.post("/api/recommend", json={"text": "table under 50"}, headers=as_user(world["alice"]))

    body = r.json()
    assert body["parsed"]["budget_max_cents"] == 5_000
    assert body["recommendations"] == []
    assert [rec["pool"]["id"] for rec in body["suggestions"]] == [world["table"].id]
def test_over_budget_pools_in_the_category_are_suggestions_cheapest_first(client, session, world, claude):
    retailer_id = session.get(Product, world["table"].product_id).retailer_id
    cheaper = _add_pool(session, retailer_id, "Pine Table", "dining_table", ["pine"])
    session.get(Product, cheaper.product_id).list_price_cents = 40_000
    session.commit()
    claude.output = {"parsed": {}, "pool_matches": [{"pool_id": world["sofa"].id, "fit_score": 99}],
                     "hidden_matches": []}

    r = client.post("/api/recommend", json={"text": "table under 200"}, headers=as_user(world["alice"]))

    body = r.json()
    assert body["recommendations"] == []
    assert [rec["pool"]["id"] for rec in body["suggestions"]] == [cheaper.id, world["table"].id]


def test_a_vague_wish_falls_back_to_the_models_picks(client, world, claude):
    claude.output = {"parsed": {}, "pool_matches": [{"pool_id": world["sofa"].id, "fit_score": 80},
                                                     {"pool_id": world["done"].id, "fit_score": 95}],
                     "suggestions": [{"pool_id": world["lamp"].id, "fit_score": 70}], "hidden_matches": []}

    r = client.post("/api/recommend", json={"text": "something cozy for movie night"}, headers=as_user(world["alice"]))

    assert [rec["pool"]["id"] for rec in r.json()["recommendations"]] == [world["sofa"].id]  # completed Pool dropped
    assert [rec["pool"]["id"] for rec in r.json()["suggestions"]] == [world["lamp"].id]


def test_a_vague_wish_the_model_maps_to_a_category_is_filtered_in_code(client, session, world, claude):
    claude.output = {"parsed": {"category": "dining_table"}, "pool_matches": [], "hidden_matches": []}

    r = client.post("/api/recommend", json={"text": "somewhere to eat with friends"}, headers=as_user(world["alice"]))

    assert [rec["pool"]["id"] for rec in r.json()["recommendations"]] == [world["table"].id]


def test_a_category_the_model_makes_up_is_ignored(client, world, claude):
    claude.output = {"parsed": {"category": "hammock"}, "pool_matches": [{"pool_id": world["sofa"].id,
                                                                            "fit_score": 80}],
                     "hidden_matches": []}

    r = client.post("/api/recommend", json={"text": "somewhere to relax"}, headers=as_user(world["alice"]))

    assert r.json()["parsed"]["category"] is None
    assert [rec["pool"]["id"] for rec in r.json()["recommendations"]] == [world["sofa"].id]


def test_missing_parsed_fields_come_back_as_null(client, world, claude):
    claude.output = {"parsed": {}, "pool_matches": [], "hidden_matches": []}

    r = client.post("/api/recommend", json={"text": "something nice"}, headers=as_user(world["alice"]))

    assert r.json()["parsed"] == {"category": None, "budget_max_cents": None, "style_tags": [], "size_notes": None}
    assert r.json()["recommendations"] == []


def test_a_claude_error_returns_502_and_saves_no_wish(client, session, world, claude):
    claude.error = RecommenderError("Claude API error (529)")

    r = client.post("/api/recommend", json={"text": "a table"}, headers=as_user(world["alice"]))

    assert_error(r, 502, "recommender_unavailable")
    assert session.exec(select(Wish)).all() == []


def test_blank_wish_is_rejected_without_calling_claude(client, world, claude):
    assert_error(client.post("/api/recommend", json={"text": "   "}, headers=as_user(world["alice"])),
                 422, "invalid_request")
    assert_error(client.post("/api/recommend", json={}, headers=as_user(world["alice"])), 422, "invalid_request")
    assert claude.prompts == []


def test_recommend_requires_a_user(client, world, claude):
    assert_error(client.post("/api/recommend", json={"text": "a table"}), 401, "forbidden")


# --- the OpenAI adapter -------------------------------------------------------


class _FakeOpenAI:
    """Stands in for openai.OpenAI: `chat.completions.parse` returns or raises what the test sets."""

    result = None
    calls: list[dict] = []

    def __init__(self, **_):
        self.chat = self
        self.completions = self

    def parse(self, **kwargs):
        _FakeOpenAI.calls.append(kwargs)
        if isinstance(_FakeOpenAI.result, Exception):
            raise _FakeOpenAI.result
        return _FakeOpenAI.result


@pytest.fixture
def fake_sdk(monkeypatch):
    _FakeOpenAI.result = None
    _FakeOpenAI.calls = []
    monkeypatch.setattr(recommender.openai, "OpenAI", _FakeOpenAI)
    return _FakeOpenAI


def _response(finish_reason="stop", parsed=None, refusal=None):
    message = SimpleNamespace(parsed=parsed, refusal=refusal)
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish_reason, message=message)])


def test_complete_uses_configured_model_minimal_reasoning_and_structured_output(fake_sdk, monkeypatch):
    monkeypatch.setattr(recommender.config, "OPENAI_MODEL", "gpt-test-model")
    out = RecommenderOutput.model_validate({"parsed": PARSED, "pool_matches": [], "hidden_matches": []})
    fake_sdk.result = _response(parsed=out)

    assert recommender.complete("the prompt") == out
    [call] = fake_sdk.calls
    assert call["model"] == "gpt-test-model"
    assert call["reasoning_effort"] == "minimal"
    assert call["response_format"] is RecommenderOutput
    assert call["messages"][-1] == {"role": "user", "content": "the prompt"}


@pytest.mark.parametrize("result", [
    openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions")),
    openai.InternalServerError("overloaded", response=httpx.Response(
        500, request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions")), body=None),
    _response(refusal="no"),
    _response(finish_reason="length"),
])
def test_complete_turns_every_model_failure_into_recommender_error(fake_sdk, result):
    fake_sdk.result = result
    with pytest.raises(RecommenderError):
        recommender.complete("the prompt")


def _add_pool(session, retailer_id, name, category, tags, description=""):
    prod = Product(retailer_id=retailer_id, name=name, category=category, style_tags=tags, description=description,
                   list_price_cents=80_000, floor_price_cents=50_000, visibility="public", created_at=T0)
    session.add(prod)
    session.commit()
    pool = Pool(product_id=prod.id, status="open", opened_at=T0, deadline=T0 + timedelta(days=2))
    session.add(pool)
    session.commit()
    session.add(Tier(pool_id=pool.id, ordinal=1, min_participants=3, discount_cents=10_000))
    session.commit()
    return pool


def test_a_material_search_shows_only_pools_with_that_material_even_when_the_model_is_sloppy(
        client, session, world, claude):
    retailer_id = world["table"].product_id and session.get(Product, world["table"].product_id).retailer_id
    oak = _add_pool(session, retailer_id, "Solid Oak Side Table", "table", ["oak"])
    teak_desk = _add_pool(session, retailer_id, "Restored Teak Desk", "desk", ["teak"])
    walnut_shelf = _add_pool(session, retailer_id, "Tall Bookcase", "bookshelf", ["mid-century"],
                             description="Tall walnut bookcase.")
    claude.output = {
        "parsed": {"category": "null", "budget_max_cents": None, "style_tags": ["walnut"], "size_notes": None},
        "pool_matches": [{"pool_id": oak.id, "fit_score": 95}, {"pool_id": teak_desk.id, "fit_score": 90}],
        "suggestions": [{"pool_id": oak.id, "fit_score": 80}],
        "hidden_matches": [],
    }

    r = client.post("/api/recommend", json={"text": "walnut"}, headers=as_user(world["alice"]))

    body = r.json()
    shown = {rec["pool"]["id"] for rec in body["recommendations"]}
    assert body["parsed"]["category"] is None
    # the model's off-material picks are gone; the walnut Pools it skipped are found anyway
    assert shown == {world["table"].id, world["sofa"].id, world["lamp"].id, walnut_shelf.id}  # all walnut-tagged
    assert body["suggestions"] == []


def test_a_material_search_is_stable_across_different_model_answers(client, session, world, claude):
    outputs = [
        {"parsed": {"style_tags": ["walnut"]}, "pool_matches": [], "hidden_matches": []},
        {"parsed": {"style_tags": []},
         "pool_matches": [{"pool_id": world["sofa"].id, "fit_score": 61}], "hidden_matches": []},
    ]
    results = []
    for output in outputs:
        claude.output = output
        r = client.post("/api/recommend", json={"text": "walnut"}, headers=as_user(world["alice"]))
        results.append({rec["pool"]["id"] for rec in r.json()["recommendations"]})
    assert results[0] == results[1] == {world["table"].id, world["sofa"].id, world["lamp"].id}


def test_a_table_wish_covers_coffee_tables_but_a_chair_wish_covers_seating(client, session, world, claude):
    retailer_id = session.get(Product, world["table"].product_id).retailer_id
    coffee = _add_pool(session, retailer_id, "Low Coffee Table", "table", ["oak"])
    armchair = _add_pool(session, retailer_id, "Accent Armchair", "seating", ["oak"])
    claude.output = {
        "parsed": {"category": "table", "style_tags": []},
        "pool_matches": [{"pool_id": coffee.id, "fit_score": 90}, {"pool_id": world["table"].id, "fit_score": 85},
                         {"pool_id": armchair.id, "fit_score": 70}],
        "hidden_matches": [],
    }
    r = client.post("/api/recommend", json={"text": "a table"}, headers=as_user(world["alice"]))
    assert [x["pool"]["id"] for x in r.json()["recommendations"]] == [world["table"].id, coffee.id]
    assert r.json()["suggestions"] == []  # the model's armchair pick is not a table

    r = client.post("/api/recommend", json={"text": "a chair"}, headers=as_user(world["alice"]))
    assert [x["pool"]["id"] for x in r.json()["recommendations"]] == [armchair.id]
