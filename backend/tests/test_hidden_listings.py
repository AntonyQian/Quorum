"""Ticket #22: Hidden Listings, demand stats, and Launch (SPEC §1, §6, §8 Retailer + Demo)."""

from datetime import timedelta

import pytest

from app.models import DemandHit, Product, Retailer, User, Wish

from tests.conftest import T0, as_user, assert_error

LAUNCH = dict(deadline_days=14, stock_cap=None, tiers=[
    dict(min_participants=10, discount_cents=15_000),
    dict(min_participants=25, discount_cents=25_000),
])


@pytest.fixture
def world(session):
    """Oak & Co. with a Hidden Listing that two shoppers wished for, Nordlund with one of its own, and simulated
    shoppers for the demo panel."""
    oak = Retailer(name="Oak & Co.")
    nord = Retailer(name="Nordlund")
    session.add_all([oak, nord])
    session.commit()
    oak_login = User(name="Oak login", role="retailer", retailer_id=oak.id)
    nord_login = User(name="Nordlund login", role="retailer", retailer_id=nord.id)
    alice = User(name="Alice", role="shopper", card_label="Visa •••• 4242")
    bob = User(name="Bob", role="shopper", card_label="Visa •••• 4242")
    carol = User(name="Carol", role="shopper", card_label="Visa •••• 4242")
    sims = [User(name=f"Sim Shopper {i}", role="shopper", is_simulated=True, card_label="Visa •••• 4242")
            for i in range(5)]
    session.add_all([oak_login, nord_login, alice, bob, carol, *sims])
    session.commit()
    table = Product(retailer_id=oak.id, name="Walnut Dining Table", category="table", style_tags=["walnut"],
                    list_price_cents=150_000, floor_price_cents=100_000, visibility="hidden",
                    demand_threshold=10, created_at=T0)
    chair = Product(retailer_id=nord.id, name="Birch Chair", category="chair",
                    list_price_cents=30_000, floor_price_cents=20_000, visibility="hidden", created_at=T0)
    session.add_all([table, chair])
    session.commit()
    for user, text, days_ago in [(alice, "walnut dining table for 4", 1), (bob, "big wooden table", 10)]:
        wish = Wish(user_id=user.id, text=text, created_at=T0 - timedelta(days=days_ago))
        session.add(wish)
        session.commit()
        session.add(DemandHit(product_id=table.id, user_id=user.id, wish_id=wish.id, created_at=wish.created_at))
    session.commit()
    return dict(oak_login=oak_login, nord_login=nord_login, alice=alice, bob=bob, carol=carol, sims=sims,
                table=table, chair=chair)


def notifications(client, user):
    r = client.get("/api/me/notifications", headers=as_user(user))
    assert r.status_code == 200, r.text
    return r.json()["items"]


# --- POST /retailer/products/{id}/launch ---------------------------------------

def test_launch_opens_a_public_pool_on_the_hidden_listing(client, world):
    table = world["table"]
    r = client.post(f"/api/retailer/products/{table.id}/launch", json=LAUNCH, headers=as_user(world["oak_login"]))
    assert r.status_code == 200, r.text
    pool = r.json()
    assert pool["status"] == "open"
    assert pool["product"]["id"] == table.id
    assert [t["price_cents"] for t in pool["tiers"]] == [135_000, 125_000]
    assert pool["time_left_seconds"] == 14 * 24 * 3600
    assert pool["my_membership"] is None

    products = client.get("/api/retailer/products", headers=as_user(world["oak_login"])).json()
    assert products[0]["visibility"] == "public"
    assert products[0]["pool"]["id"] == pool["id"]


def test_launch_notifies_every_shopper_with_a_demand_hit(client, world):
    table = world["table"]
    pool = client.post(f"/api/retailer/products/{table.id}/launch", json=LAUNCH,
                       headers=as_user(world["oak_login"])).json()

    for shopper in (world["alice"], world["bob"]):
        items = notifications(client, shopper)
        assert len(items) == 1
        assert items[0]["kind"] == "pool_launched"
        assert items[0]["title"] == "The Walnut Dining Table you asked about is now a Pool"
        assert items[0]["link"] == f"/pools/{pool['id']}"
    assert notifications(client, world["carol"]) == []


def test_launch_with_invalid_tiers_leaves_the_listing_hidden_and_notifies_no_one(client, world):
    table = world["table"]
    below_floor = dict(LAUNCH, tiers=[dict(min_participants=10, discount_cents=60_000)])
    r = client.post(f"/api/retailer/products/{table.id}/launch", json=below_floor,
                    headers=as_user(world["oak_login"]))
    assert_error(r, 400, "invalid_tiers")
    products = client.get("/api/retailer/products", headers=as_user(world["oak_login"])).json()
    assert products[0]["visibility"] == "hidden" and products[0]["pool"] is None
    assert notifications(client, world["alice"]) == []


def test_launching_a_public_product_again_is_invalid(client, world):
    table = world["table"]
    client.post(f"/api/retailer/products/{table.id}/launch", json=LAUNCH, headers=as_user(world["oak_login"]))
    r = client.post(f"/api/retailer/products/{table.id}/launch", json=LAUNCH, headers=as_user(world["oak_login"]))
    assert_error(r, 400, "invalid_request")


def test_cannot_launch_another_retailers_product(client, world):
    r = client.post(f"/api/retailer/products/{world['chair'].id}/launch", json=LAUNCH,
                    headers=as_user(world["oak_login"]))
    assert_error(r, 404, "not_found")


# --- Hidden Listings stay hidden from shoppers ------------------------------------

ALL_STATUSES = "open,locked,completed,failed"


def shopper_pool_product_ids(client, user):
    r = client.get(f"/api/pools?status={ALL_STATUSES}", headers=as_user(user))
    assert r.status_code == 200, r.text
    return [p["product"]["id"] for p in r.json()]


def test_hidden_listing_is_not_shown_to_shoppers_until_launched(client, world):
    table = world["table"]
    assert table.id not in shopper_pool_product_ids(client, world["alice"])
    client.post(f"/api/retailer/products/{table.id}/launch", json=LAUNCH, headers=as_user(world["oak_login"]))
    assert table.id in shopper_pool_product_ids(client, world["alice"])


def test_product_hidden_again_after_its_pool_ended_is_not_shown_to_shoppers(client, world):
    table = world["table"]
    pool = client.post(f"/api/retailer/products/{table.id}/launch", json=LAUNCH,
                       headers=as_user(world["oak_login"])).json()
    client.post("/api/demo/clock/advance", json={"to_deadline_of_pool": pool["id"]})  # no Members: fails
    r = client.patch(f"/api/retailer/products/{table.id}", json={"visibility": "hidden"},
                     headers=as_user(world["oak_login"]))
    assert r.status_code == 200, r.text

    assert table.id not in shopper_pool_product_ids(client, world["alice"])
    assert_error(client.get(f"/api/pools/{pool['id']}", headers=as_user(world["alice"])), 404, "not_found")


# --- GET /retailer/products/{id}/demand ------------------------------------------

def test_demand_reports_hits_last_7_days_by_sim_clock_threshold_and_recent_wishes(client, world):
    r = client.get(f"/api/retailer/products/{world['table'].id}/demand", headers=as_user(world["oak_login"]))
    assert r.status_code == 200, r.text
    assert r.json() == {
        "total_hits": 2,
        "last_7_days": 1,
        "threshold": 10,
        "recent_wishes": [
            {"text": "walnut dining table for 4", "created_at": "2026-10-16T12:00:00Z"},
            {"text": "big wooden table", "created_at": "2026-10-07T12:00:00Z"},
        ],
    }


def test_last_7_days_follows_the_sim_clock(client, world):
    client.post("/api/demo/clock/advance", json={"days": 7})
    r = client.get(f"/api/retailer/products/{world['table'].id}/demand", headers=as_user(world["oak_login"]))
    assert r.json()["total_hits"] == 2
    assert r.json()["last_7_days"] == 0


def test_cannot_read_another_retailers_demand(client, world):
    r = client.get(f"/api/retailer/products/{world['chair'].id}/demand", headers=as_user(world["oak_login"]))
    assert_error(r, 404, "not_found")


@pytest.mark.parametrize("action", ["join", "leave"])
def test_shoppers_cannot_join_or_leave_a_pool_on_a_hidden_product(client, world, action):
    table = world["table"]
    pool = client.post(f"/api/retailer/products/{table.id}/launch", json=LAUNCH,
                       headers=as_user(world["oak_login"])).json()
    client.post("/api/demo/clock/advance", json={"to_deadline_of_pool": pool["id"]})  # no Members: fails
    client.patch(f"/api/retailer/products/{table.id}", json={"visibility": "hidden"},
                 headers=as_user(world["oak_login"]))

    r = client.post(f"/api/pools/{pool['id']}/{action}", headers=as_user(world["alice"]))
    assert_error(r, 404, "not_found")


# --- POST /demo/products/{id}/simulate-demand ------------------------------------

def simulate_demand(client, product, count):
    return client.post(f"/api/demo/products/{product.id}/simulate-demand", json={"count": count})


def test_simulate_demand_adds_demand_hits_from_simulated_shoppers(client, world):
    r = simulate_demand(client, world["table"], 3)
    assert r.status_code == 200, r.text
    assert r.json() == {"total_hits": 5}

    demand = client.get(f"/api/retailer/products/{world['table'].id}/demand",
                        headers=as_user(world["oak_login"])).json()
    assert demand["total_hits"] == 5 and demand["last_7_days"] == 4
    assert len(demand["recent_wishes"]) == 5


def test_simulated_shoppers_hit_a_product_at_most_once(client, world):
    simulate_demand(client, world["table"], 4)
    r = simulate_demand(client, world["table"], 4)  # only 1 of the 5 simulated shoppers is left
    assert r.json() == {"total_hits": 7}


def test_launch_notifies_simulated_shoppers_with_demand_hits_too(client, world):
    simulate_demand(client, world["table"], 2)
    client.post(f"/api/retailer/products/{world['table'].id}/launch", json=LAUNCH,
                headers=as_user(world["oak_login"]))
    notified = [s for s in world["sims"] if notifications(client, s)]
    assert len(notified) == 2


def test_reaching_the_demand_threshold_alerts_the_retailer_once(client, world):
    oak = as_user(world["oak_login"])
    client.patch(f"/api/retailer/products/{world['table'].id}", json={"demand_threshold": 4}, headers=oak)
    simulate_demand(client, world["table"], 1)
    assert client.get("/api/retailer/notifications", headers=oak).json()["items"] == []

    simulate_demand(client, world["table"], 1)
    items = client.get("/api/retailer/notifications", headers=oak).json()["items"]
    assert len(items) == 1
    assert items[0]["kind"] == "demand_threshold"
    assert "Walnut Dining Table" in items[0]["title"]

    simulate_demand(client, world["table"], 2)
    assert len(client.get("/api/retailer/notifications", headers=oak).json()["items"]) == 1


def test_lowering_the_threshold_to_the_current_hits_alerts_the_retailer_once(client, world):
    oak = as_user(world["oak_login"])
    table = world["table"]  # 2 Demand Hits, threshold 10
    r = client.patch(f"/api/retailer/products/{table.id}", json={"demand_threshold": 2}, headers=oak)
    assert r.status_code == 200, r.text
    items = client.get("/api/retailer/notifications", headers=oak).json()["items"]
    assert [i["kind"] for i in items] == ["demand_threshold"]

    client.patch(f"/api/retailer/products/{table.id}", json={"demand_threshold": 1}, headers=oak)
    simulate_demand(client, table, 2)
    assert len(client.get("/api/retailer/notifications", headers=oak).json()["items"]) == 1


def test_hits_passing_a_threshold_set_below_them_still_alert_once(client, world):
    oak = as_user(world["oak_login"])
    table = world["table"]
    client.patch(f"/api/retailer/products/{table.id}", json={"demand_threshold": None}, headers=oak)
    simulate_demand(client, table, 2)  # 4 hits, no threshold
    assert client.get("/api/retailer/notifications", headers=oak).json()["items"] == []
    client.patch(f"/api/retailer/products/{table.id}", json={"demand_threshold": 3}, headers=oak)
    simulate_demand(client, table, 1)
    assert len(client.get("/api/retailer/notifications", headers=oak).json()["items"]) == 1


@pytest.mark.parametrize("threshold", [0, -3])
def test_demand_threshold_below_1_is_invalid(client, world, threshold):
    r = client.patch(f"/api/retailer/products/{world['table'].id}", json={"demand_threshold": threshold},
                     headers=as_user(world["oak_login"]))
    assert_error(r, 400, "invalid_request")
    body = dict(name="Ash Stool", description="", category="stool", style_tags=[], dimensions="", image_url="",
                list_price_cents=10_000, floor_price_cents=8_000, visibility="hidden", demand_threshold=threshold)
    r = client.post("/api/retailer/products", json=body, headers=as_user(world["oak_login"]))
    assert_error(r, 400, "invalid_request")


def test_demand_threshold_cannot_be_set_on_a_public_product(client, world):
    table = world["table"]
    client.post(f"/api/retailer/products/{table.id}/launch", json=LAUNCH, headers=as_user(world["oak_login"]))
    r = client.patch(f"/api/retailer/products/{table.id}", json={"demand_threshold": 5},
                     headers=as_user(world["oak_login"]))
    assert_error(r, 400, "invalid_request")


def test_simulate_demand_on_unknown_product_is_not_found(client, world):
    r = client.post("/api/demo/products/9999/simulate-demand", json={"count": 1})
    assert_error(r, 404, "not_found")


@pytest.mark.parametrize("count", [-1, 201])
def test_simulate_demand_count_out_of_range_is_invalid(client, world, count):
    assert_error(simulate_demand(client, world["table"], count), 422, "invalid_request")


@pytest.mark.parametrize("method,path", [
    ("post", "/api/retailer/products/1/launch"),
    ("get", "/api/retailer/products/1/demand"),
])
def test_shoppers_cannot_launch_or_read_demand(client, world, method, path):
    kwargs = {"json": LAUNCH} if method == "post" else {}
    r = getattr(client, method)(path, headers=as_user(world["alice"]), **kwargs)
    assert_error(r, 403, "forbidden")
