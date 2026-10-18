"""Ticket #26: the recommendation call also scores Hidden Listings and records Demand Hits (SPEC §6, ADR 0002).

Tested through POST /api/recommend with the Claude call stubbed at `recommender.complete`; Demand Hits and the
threshold alert are observed through the retailer endpoints.
"""

import json
import re
from datetime import timedelta

import pytest

from app.models import Pool, Product, Retailer, Tier, User
from app.services import recommender
from app.services.recommender import RecommenderOutput

from tests.conftest import T0, as_user

FLOOR = 100_000


@pytest.fixture
def world(session):
    oak = Retailer(name="Oak & Co.")
    session.add(oak)
    session.commit()
    oak_login = User(name="Oak login", role="retailer", retailer_id=oak.id)
    shoppers = [User(name=f"Shopper {i}", role="shopper") for i in range(4)]
    session.add_all([oak_login, *shoppers])
    session.commit()
    table = Product(retailer_id=oak.id, name="Walnut Dining Table", category="dining_table", style_tags=["walnut"],
                    dimensions="180x90 cm", list_price_cents=150_000, floor_price_cents=FLOOR,
                    visibility="hidden", demand_threshold=3, created_at=T0)
    sofa = Product(retailer_id=oak.id, name="Linen Sofa", category="sofa", list_price_cents=90_000,
                   floor_price_cents=60_000, visibility="public", created_at=T0)
    session.add_all([table, sofa])
    session.commit()
    pool = Pool(product_id=sofa.id, opened_at=T0, deadline=T0 + timedelta(days=2))
    session.add(pool)
    session.commit()
    session.add(Tier(pool_id=pool.id, ordinal=1, min_participants=3, discount_cents=10_000))
    session.commit()
    return dict(oak_login=oak_login, shoppers=shoppers, table=table, sofa=sofa, pool=pool)


@pytest.fixture
def claude(monkeypatch):
    """Stub the Claude call: records each prompt and returns `claude.output`."""

    class Stub:
        def __init__(self):
            self.prompts = []
            self.output = None

        def __call__(self, prompt):
            self.prompts.append(prompt)
            return RecommenderOutput.model_validate(self.output)

    stub = Stub()
    monkeypatch.setattr(recommender, "complete", stub)
    return stub


def wish(client, claude, shopper, product, fit_score, budget=None, pool_matches=()):
    claude.output = {
        "parsed": {"category": "dining_table", "budget_max_cents": budget, "style_tags": [], "size_notes": None},
        "pool_matches": list(pool_matches),
        "hidden_matches": [{"product_id": product.id, "fit_score": fit_score}],
    }
    r = client.post("/api/recommend", json={"text": "walnut dining table for 4"}, headers=as_user(shopper))
    assert r.status_code == 200, r.text
    return r


def total_hits(client, world):
    r = client.get(f"/api/retailer/products/{world['table'].id}/demand", headers=as_user(world["oak_login"]))
    assert r.status_code == 200, r.text
    return r.json()["total_hits"]


def retailer_alerts(client, world):
    items = client.get("/api/retailer/notifications", headers=as_user(world["oak_login"])).json()["items"]
    return [n for n in items if n["kind"] == "demand_threshold"]


def test_hidden_listings_are_in_the_prompt_with_their_floor_price(client, world, claude):
    wish(client, claude, world["shoppers"][0], world["table"], 0)

    [prompt] = claude.prompts
    section = re.search(r"<hidden_listings>\n(.*)\n</hidden_listings>", prompt, re.S).group(1)
    assert json.loads(section) == [{
        "id": world["table"].id, "name": "Walnut Dining Table", "category": "dining_table",
        "style_tags": ["walnut"], "dimensions": "180x90 cm", "floor_price_cents": FLOOR,
    }]


@pytest.mark.parametrize("fit_score, budget, hit", [
    (60, None, True),         # no budget stated
    (60, FLOOR, True),        # budget exactly at the Floor Price
    (95, FLOOR + 1, True),
    (59, None, False),        # fit too low
    (90, FLOOR - 1, False),   # budget below the Floor Price
])
def test_a_demand_hit_needs_fit_60_and_a_budget_missing_or_at_least_the_floor(client, world, claude,
                                                                               fit_score, budget, hit):
    wish(client, claude, world["shoppers"][0], world["table"], fit_score, budget)

    assert total_hits(client, world) == (1 if hit else 0)


def test_a_shopper_counts_once_per_product_however_many_wishes_match(client, world, claude):
    alice, bob = world["shoppers"][:2]
    wish(client, claude, alice, world["table"], 90)
    wish(client, claude, alice, world["table"], 80)
    wish(client, claude, bob, world["table"], 70)

    assert total_hits(client, world) == 2


def test_the_retailer_is_alerted_once_when_the_threshold_is_reached(client, world, claude):
    a, b, c, d = world["shoppers"]
    wish(client, claude, a, world["table"], 90)
    wish(client, claude, b, world["table"], 90)
    assert retailer_alerts(client, world) == []

    wish(client, claude, c, world["table"], 90)  # 3rd hit = Demand Threshold
    [alert] = retailer_alerts(client, world)
    assert "Walnut Dining Table" in alert["title"]

    wish(client, claude, d, world["table"], 90)  # past the threshold
    wish(client, claude, c, world["table"], 90)  # duplicate
    assert len(retailer_alerts(client, world)) == 1


def test_hidden_matches_never_appear_in_the_response(client, world, claude):
    r = wish(client, claude, world["shoppers"][0], world["table"], 95, pool_matches=[
        {"pool_id": world["pool"].id, "fit_score": 70, "reason": "Linen, seats 3."},
    ])

    body = r.json()
    assert set(body) == {"wish_id", "parsed", "recommendations"}
    assert [rec["pool"]["id"] for rec in body["recommendations"]] == [world["pool"].id]
    assert "Walnut Dining Table" not in r.text
    assert total_hits(client, world) == 1


def test_matches_on_products_that_are_not_hidden_listings_are_ignored(client, session, world, claude):
    wish(client, claude, world["shoppers"][0], world["sofa"], 95)  # public Product
    claude.output["hidden_matches"] = [{"product_id": 9999, "fit_score": 95}]  # made up
    r = client.post("/api/recommend", json={"text": "anything"}, headers=as_user(world["shoppers"][1]))

    assert r.status_code == 200, r.text
    sofa_demand = client.get(f"/api/retailer/products/{world['sofa'].id}/demand",
                             headers=as_user(world["oak_login"]))
    assert sofa_demand.json()["total_hits"] == 0
    assert total_hits(client, world) == 0
