"""Ticket #8: Accounts and Pool read endpoints with Tier pricing (SPEC §3, §4 Pricing, §8)."""

from datetime import timedelta

import pytest

from app.models import Pool, PoolMember, Product, Retailer, Tier, User
from app.services import clock, pool_engine

from tests.conftest import T0

USER_KEYS = {"id", "name", "role", "retailer_id", "card_label", "is_simulated"}
CARD_KEYS = {"id", "name", "image_url", "category", "style_tags", "retailer_name", "list_price_cents"}
SUMMARY_KEYS = {
    "id", "product", "status", "participants", "tiers", "current_price_cents",
    "next_tier", "deadline", "time_left_seconds", "stock_cap",
}
TIER_KEYS = {"ordinal", "min_participants", "discount_cents", "price_cents", "reached"}


# --- pricing helpers ---------------------------------------------------------

PRODUCT = Product(retailer_id=1, name="Sofa", category="sofa", list_price_cents=100_000,
                  floor_price_cents=50_000, created_at=T0)
TIERS = [
    Tier(pool_id=1, ordinal=1, min_participants=3, discount_cents=10_000),
    Tier(pool_id=1, ordinal=2, min_participants=5, discount_cents=15_000),
    Tier(pool_id=1, ordinal=3, min_participants=8, discount_cents=20_000),
]


def test_pricing_with_no_tier_reached_quotes_tier_one_and_points_at_it():
    assert pool_engine.current_tier(TIERS, 2) is None
    assert pool_engine.current_price(PRODUCT, TIERS, 2) == 90_000
    assert pool_engine.next_tier(TIERS, 2).ordinal == 1


def test_pricing_with_tier_one_reached_uses_its_price_and_points_at_tier_two():
    assert pool_engine.current_tier(TIERS, 4).ordinal == 1
    assert pool_engine.current_price(PRODUCT, TIERS, 4) == 90_000
    assert pool_engine.next_tier(TIERS, 4).ordinal == 2


def test_pricing_with_top_tier_reached_has_no_next_tier():
    assert pool_engine.current_tier(TIERS, 8).ordinal == 3
    assert pool_engine.current_price(PRODUCT, TIERS, 8) == 80_000
    assert pool_engine.next_tier(TIERS, 8) is None


# --- fixtures ----------------------------------------------------------------

@pytest.fixture
def world(session):
    """Two retailers, Alice, a simulated shopper, and two Pools on different categories."""
    oak = Retailer(name="Oak & Co.")
    nord = Retailer(name="Nordlund")
    session.add_all([oak, nord])
    session.commit()
    alice = User(name="Alice", role="shopper")
    bob = User(name="Bob", role="shopper", card_label="Visa •••• 4242")
    owner = User(name="Oak Owner", role="retailer", retailer_id=oak.id)
    sims = [User(name=f"Sim {i}", role="shopper", is_simulated=True, card_label="Visa •••• 4242")
            for i in range(6)]
    session.add_all([alice, bob, owner, *sims])
    sofa = Product(retailer_id=oak.id, name="Walnut Sofa", description="Solid walnut", category="sofa",
                   style_tags=["walnut"], dimensions="200x90", image_url="http://img/sofa",
                   list_price_cents=100_000, floor_price_cents=50_000, visibility="public", created_at=T0)
    table = Product(retailer_id=nord.id, name="Birch Table", category="dining_table",
                    list_price_cents=60_000, floor_price_cents=30_000, visibility="public", created_at=T0)
    session.add_all([sofa, table])
    session.commit()
    sofa_pool = Pool(product_id=sofa.id, opened_at=T0, deadline=T0 + timedelta(days=3, hours=2), stock_cap=20)
    table_pool = Pool(product_id=table.id, opened_at=T0, deadline=T0 + timedelta(days=10))
    session.add_all([sofa_pool, table_pool])
    session.commit()
    session.add_all([
        Tier(pool_id=sofa_pool.id, ordinal=1, min_participants=3, discount_cents=10_000),
        Tier(pool_id=sofa_pool.id, ordinal=2, min_participants=5, discount_cents=15_000),
        Tier(pool_id=table_pool.id, ordinal=1, min_participants=10, discount_cents=5_000),
    ])
    # Two active sim members plus one who left: participants == 2, no Tier reached.
    for sim in sims[:2]:
        session.add(PoolMember(pool_id=sofa_pool.id, user_id=sim.id, joined_at=T0))
    session.add(PoolMember(pool_id=sofa_pool.id, user_id=sims[2].id, status="left", joined_at=T0))
    session.commit()
    return dict(alice=alice, bob=bob, owner=owner, sims=sims, sofa_pool=sofa_pool,
                table_pool=table_pool, oak=oak)


def as_user(user):
    return {"X-User-Id": str(user.id)}


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"detail"}
    assert set(body["detail"]) == {"code", "message"}
    assert body["detail"]["code"] == code
    assert isinstance(body["detail"]["message"], str) and body["detail"]["message"]


# --- accounts ----------------------------------------------------------------

def test_users_lists_real_accounts_only_by_default(client, world):
    body = client.get("/api/users").json()
    assert [u["name"] for u in body] == ["Alice", "Bob", "Oak Owner"]
    assert all(set(u) == USER_KEYS for u in body)
    assert body[2] == {"id": world["owner"].id, "name": "Oak Owner", "role": "retailer",
                       "retailer_id": world["oak"].id, "card_label": None, "is_simulated": False}


def test_users_include_simulated_adds_simulated_shoppers(client, world):
    body = client.get("/api/users", params={"include_simulated": "true"}).json()
    assert len(body) == 9
    assert sum(u["is_simulated"] for u in body) == 6


def test_me_returns_the_user_named_by_the_header(client, world):
    body = client.get("/api/me", headers=as_user(world["bob"])).json()
    assert body == {"id": world["bob"].id, "name": "Bob", "role": "shopper", "retailer_id": None,
                    "card_label": "Visa •••• 4242", "is_simulated": False}


@pytest.mark.parametrize("headers", [{}, {"X-User-Id": "9999"}, {"X-User-Id": "abc"}])
def test_me_without_a_known_user_is_an_error_in_the_spec_shape(client, world, headers):
    assert_error(client.get("/api/me", headers=headers), 401, "forbidden")


# --- pools list --------------------------------------------------------------

def test_pools_list_returns_pool_summaries(client, world):
    body = client.get("/api/pools").json()
    assert [p["id"] for p in body] == [world["sofa_pool"].id, world["table_pool"].id]
    sofa = body[0]
    assert set(sofa) == SUMMARY_KEYS
    assert set(sofa["product"]) == CARD_KEYS
    assert all(set(t) == TIER_KEYS for t in sofa["tiers"])
    assert sofa["product"]["retailer_name"] == "Oak & Co."
    assert sofa["product"]["style_tags"] == ["walnut"]
    assert sofa["status"] == "open"
    assert sofa["participants"] == 2
    assert sofa["tiers"] == [
        {"ordinal": 1, "min_participants": 3, "discount_cents": 10_000, "price_cents": 90_000, "reached": False},
        {"ordinal": 2, "min_participants": 5, "discount_cents": 15_000, "price_cents": 85_000, "reached": False},
    ]
    assert sofa["current_price_cents"] == 90_000
    assert sofa["next_tier"] == {"ordinal": 1, "needed": 1, "price_cents": 90_000}
    assert sofa["deadline"] == "2026-10-20T14:00:00Z"
    assert sofa["time_left_seconds"] == (3 * 24 + 2) * 3600
    assert sofa["stock_cap"] == 20


def test_pools_list_filters_by_category(client, world):
    body = client.get("/api/pools", params={"category": "dining_table"}).json()
    assert [p["id"] for p in body] == [world["table_pool"].id]


def test_pools_list_filters_by_status(client, world, session):
    pool = session.get(Pool, world["table_pool"].id)
    pool.status = "failed"
    session.add(pool)
    session.commit()
    assert [p["id"] for p in client.get("/api/pools").json()] == [world["sofa_pool"].id]
    body = client.get("/api/pools", params={"status": "failed"}).json()
    assert [p["id"] for p in body] == [world["table_pool"].id]


def test_time_left_follows_the_sim_clock(client, world, session):
    clock.set_now(session, T0 + timedelta(days=3))
    sofa = client.get(f"/api/pools/{world['sofa_pool'].id}").json()
    assert sofa["time_left_seconds"] == 2 * 3600


# --- pool detail -------------------------------------------------------------

def test_pool_detail_for_an_anonymous_viewer(client, world):
    body = client.get(f"/api/pools/{world['sofa_pool'].id}").json()
    assert set(body) == SUMMARY_KEYS | {"my_membership", "final_price_cents"}
    assert set(body["product"]) == CARD_KEYS | {"description", "dimensions"}
    assert body["product"]["description"] == "Solid walnut"
    assert body["product"]["dimensions"] == "200x90"
    assert body["my_membership"] is None
    assert body["final_price_cents"] is None


def test_pool_detail_my_membership_is_null_for_non_members(client, world):
    body = client.get(f"/api/pools/{world['sofa_pool'].id}", headers=as_user(world["alice"])).json()
    assert body["my_membership"] is None


def test_pool_detail_shows_the_viewers_membership(client, world):
    sim = world["sims"][0]
    body = client.get(f"/api/pools/{world['sofa_pool'].id}", headers=as_user(sim)).json()
    assert body["my_membership"] == {"status": "pending", "charged_cents": 0, "refunded_cents": 0}


def test_pool_detail_after_tier_one_reached(client, world, session):
    session.add(PoolMember(pool_id=world["sofa_pool"].id, user_id=world["sims"][3].id, joined_at=T0))
    session.commit()
    body = client.get(f"/api/pools/{world['sofa_pool'].id}").json()
    assert body["status"] == "locked"
    assert [t["reached"] for t in body["tiers"]] == [True, False]
    assert body["current_price_cents"] == 90_000
    assert body["next_tier"] == {"ordinal": 2, "needed": 2, "price_cents": 85_000}


def test_unknown_pool_is_not_found(client, world):
    assert_error(client.get("/api/pools/9999"), 404, "not_found")


# --- framework errors in the SPEC shape --------------------------------------

def test_validation_errors_use_the_spec_error_shape(client, world):
    assert_error(client.get("/api/pools/not-a-number"), 422, "invalid_request")


def test_unknown_route_uses_the_spec_error_shape(client):
    assert_error(client.get("/api/nope"), 404, "not_found")
