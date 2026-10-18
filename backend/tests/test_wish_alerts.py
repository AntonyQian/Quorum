"""A Shopper who wished for something no Pool offered is notified when a Retailer opens a fitting Pool."""

from datetime import timedelta

import pytest

from app.models import Retailer, User, Wish

from tests.conftest import T0, as_user

POOL = dict(deadline_days=14, stock_cap=None, tiers=[
    dict(min_participants=5, discount_cents=20_000),
    dict(min_participants=10, discount_cents=40_000),
])


def product_body(name="Walnut Dining Table", category="dining_table", tags=("walnut",), list_cents=150_000):
    return dict(name=name, description="Solid table", dimensions="200x90x75 cm", image_url="https://img/t.jpg",
                category=category, style_tags=list(tags), list_price_cents=list_cents,
                floor_price_cents=80_000, visibility="public", pool=POOL)


@pytest.fixture
def world(session):
    oak = Retailer(name="Oak & Co.")
    session.add(oak)
    session.commit()
    retailer = User(name="Oak login", role="retailer", retailer_id=oak.id)
    alice = User(name="Alice", role="shopper", card_label="Visa •••• 4242")
    bob = User(name="Bob", role="shopper", card_label="Visa •••• 4242")
    sim = User(name="Sim", role="shopper", is_simulated=True, card_label="Visa •••• 4242")
    session.add_all([retailer, alice, bob, sim])
    session.commit()
    return dict(retailer=retailer, alice=alice, bob=bob, sim=sim)


def wish(session, user, text, parsed):
    session.add(Wish(user_id=user.id, text=text, parsed=parsed, created_at=T0 - timedelta(hours=1)))
    session.commit()


def alerts(client, user):
    items = client.get("/api/me/notifications", headers=as_user(user)).json()["items"]
    return [n for n in items if n["kind"] == "wish_pool_opened"]


def open_product(client, world, **kw):
    r = client.post("/api/retailer/products", json=product_body(**kw), headers=as_user(world["retailer"]))
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_opening_a_fitting_pool_notifies_the_shopper(client, session, world):
    wish(session, world["alice"], "walnut dining table under $1200",
         {"category": "dining_table", "budget_max_cents": 120_000, "style_tags": ["walnut"]})
    open_product(client, world)  # best Tier price is $1,100
    (note,) = alerts(client, world["alice"])
    assert "Walnut Dining Table" in note["title"]
    assert note["link"].startswith("/pools/")
    assert not note["read"]


def test_budget_below_the_best_tier_price_is_not_notified(client, session, world):
    wish(session, world["alice"], "walnut dining table under $900",
         {"category": "dining_table", "budget_max_cents": 90_000})
    open_product(client, world)
    assert alerts(client, world["alice"]) == []


def test_other_category_or_missing_material_is_not_notified(client, session, world):
    wish(session, world["alice"], "sofa", {"category": "sofa"})
    wish(session, world["bob"], "oak dining table", {"category": "dining_table"})
    open_product(client, world)
    assert alerts(client, world["alice"]) == []
    assert alerts(client, world["bob"]) == []


def test_wish_made_after_the_pool_opened_is_not_notified(client, session, world):
    session.add(Wish(user_id=world["alice"].id, text="walnut dining table", parsed={"category": "dining_table"},
                     created_at=T0 + timedelta(days=1)))
    session.commit()
    open_product(client, world)
    assert alerts(client, world["alice"]) == []


def test_shopper_is_notified_once_per_pool_and_simulated_shoppers_are_skipped(client, session, world):
    parsed = {"category": "dining_table"}
    wish(session, world["alice"], "dining table", parsed)
    wish(session, world["alice"], "walnut dining table", parsed)
    wish(session, world["sim"], "dining table", parsed)
    open_product(client, world)
    assert len(alerts(client, world["alice"])) == 1
    assert alerts(client, world["sim"]) == []
