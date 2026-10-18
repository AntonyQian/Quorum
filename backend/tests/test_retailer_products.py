"""Ticket #21: Retailer products and public listings (SPEC §4 Validation, §8 Retailer)."""

from datetime import timedelta

import pytest

from app.models import DemandHit, Pool, PoolMember, Product, Retailer, Tier, User, Wish

from tests.conftest import T0, as_user, assert_error

RETAILER_PRODUCT_KEYS = {
    "id", "name", "image_url", "category", "style_tags", "retailer_name", "list_price_cents",
    "visibility", "floor_price_cents", "demand", "pool",
}


@pytest.fixture
def world(session):
    """Two retailers with one login each, a shopper, and one hidden Product per retailer."""
    oak = Retailer(name="Oak & Co.")
    nord = Retailer(name="Nordlund")
    session.add_all([oak, nord])
    session.commit()
    oak_login = User(name="Oak login", role="retailer", retailer_id=oak.id)
    nord_login = User(name="Nordlund login", role="retailer", retailer_id=nord.id)
    alice = User(name="Alice", role="shopper", card_label="Visa •••• 4242")
    session.add_all([oak_login, nord_login, alice])
    session.commit()
    table = Product(retailer_id=oak.id, name="Walnut Dining Table", category="table", style_tags=["walnut"],
                    list_price_cents=150_000, floor_price_cents=100_000, visibility="hidden",
                    demand_threshold=10, created_at=T0)
    chair = Product(retailer_id=nord.id, name="Birch Chair", category="chair",
                    list_price_cents=30_000, floor_price_cents=20_000, visibility="hidden", created_at=T0)
    session.add_all([table, chair])
    session.commit()
    return dict(oak=oak, nord=nord, oak_login=oak_login, nord_login=nord_login, alice=alice,
                table=table, chair=chair)


def public_body(**overrides):
    body = dict(
        name="Oak Sofa", description="Solid oak frame", category="sofa", style_tags=["oak", "modern"],
        dimensions="200x90x80 cm", image_url="https://img/sofa.jpg",
        list_price_cents=100_000, floor_price_cents=70_000, visibility="public",
        pool=dict(deadline_days=14, stock_cap=50, tiers=[
            dict(min_participants=10, discount_cents=15_000),
            dict(min_participants=25, discount_cents=25_000),
        ]),
    )
    body.update(overrides)
    return body


# --- role checks -------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("get", "/api/retailer/products"),
    ("post", "/api/retailer/products"),
    ("patch", "/api/retailer/products/1"),
    ("get", "/api/retailer/pools/1"),
])
def test_shopper_accounts_are_forbidden(client, world, method, path):
    kwargs = {"json": public_body()} if method in ("post", "patch") else {}
    r = getattr(client, method)(path, headers=as_user(world["alice"]), **kwargs)
    assert_error(r, 403, "forbidden")


# --- GET /retailer/products ----------------------------------------------------

def test_retailer_lists_only_their_own_products(client, world):
    r = client.get("/api/retailer/products", headers=as_user(world["oak_login"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert [p["name"] for p in body] == ["Walnut Dining Table"]
    assert set(body[0]) == RETAILER_PRODUCT_KEYS
    assert body[0]["retailer_name"] == "Oak & Co."
    assert body[0]["visibility"] == "hidden"
    assert body[0]["floor_price_cents"] == 100_000
    assert body[0]["pool"] is None


def test_hidden_listing_shows_demand_against_its_threshold(client, session, world):
    shoppers = [User(name=f"Shopper {i}", role="shopper", is_simulated=True) for i in range(3)]
    session.add_all(shoppers)
    session.commit()
    for i, s in enumerate(shoppers):
        wish = Wish(user_id=s.id, text="walnut table", created_at=T0)
        session.add(wish)
        session.commit()
        # One old hit (10 days ago), two recent ones.
        when = T0 - timedelta(days=10) if i == 0 else T0 - timedelta(days=1)
        session.add(DemandHit(product_id=world["table"].id, user_id=s.id, wish_id=wish.id, created_at=when))
    session.commit()

    r = client.get("/api/retailer/products", headers=as_user(world["oak_login"]))
    assert r.json()[0]["demand"] == {"total_hits": 3, "last_7_days": 2, "threshold": 10, "threshold_reached": False}


# --- POST /retailer/products ---------------------------------------------------

def test_creating_a_public_product_opens_a_pool_and_lists_it(client, world):
    r = client.post("/api/retailer/products", json=public_body(), headers=as_user(world["oak_login"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == RETAILER_PRODUCT_KEYS
    assert body["visibility"] == "public"
    assert body["retailer_name"] == "Oak & Co."
    assert body["demand"] is None
    pool = body["pool"]
    assert pool["status"] == "open"
    assert pool["participants"] == 0
    assert pool["stock_cap"] == 50
    assert [(t["min_participants"], t["price_cents"]) for t in pool["tiers"]] == [(10, 85_000), (25, 75_000)]
    assert pool["deadline"] == "2026-10-31T12:00:00Z"  # T0 + 14 days on the Sim Clock

    listed = client.get("/api/retailer/products", headers=as_user(world["oak_login"])).json()
    assert [p["name"] for p in listed] == ["Walnut Dining Table", "Oak Sofa"]
    public = client.get("/api/pools").json()
    assert [p["product"]["name"] for p in public] == ["Oak Sofa"]


def test_creating_a_hidden_listing_collects_demand_and_opens_no_pool(client, world):
    body = public_body(visibility="hidden", demand_threshold=15, pool=None)
    r = client.post("/api/retailer/products", json=body, headers=as_user(world["oak_login"]))
    assert r.status_code == 200, r.text
    assert r.json()["pool"] is None
    assert r.json()["demand"] == {"total_hits": 0, "last_7_days": 0, "threshold": 15, "threshold_reached": False}
    assert client.get("/api/pools").json() == []


def tiers(*pairs):
    return [dict(min_participants=m, discount_cents=d) for m, d in pairs]


# list 100_000, floor 70_000: discounts above 30_000 put a Tier below the Floor Price.
@pytest.mark.parametrize("pool", [
    dict(deadline_days=14, tiers=[]),                                          # no Tiers
    dict(deadline_days=14, tiers=tiers((5, 1_000), (10, 2_000), (15, 3_000), (20, 4_000))),  # 4 Tiers
    dict(deadline_days=14, tiers=tiers((10, 5_000), (10, 8_000))),             # participants not increasing
    dict(deadline_days=14, tiers=tiers((10, 8_000), (20, 8_000))),             # discounts not increasing
    dict(deadline_days=14, tiers=tiers((10, 8_000), (5, 9_000))),              # participants decreasing
    dict(deadline_days=14, tiers=tiers((10, 30_001))),                         # Tier 1 below Floor Price
    dict(deadline_days=14, tiers=tiers((10, 10_000), (20, 35_000))),           # Tier 2 below Floor Price
    dict(deadline_days=0, tiers=tiers((10, 10_000))),                          # Deadline too short
    dict(deadline_days=31, tiers=tiers((10, 10_000))),                         # Deadline too long
])
def test_invalid_pools_are_refused_with_invalid_tiers(client, world, pool):
    r = client.post("/api/retailer/products", json=public_body(pool=pool), headers=as_user(world["oak_login"]))
    assert_error(r, 400, "invalid_tiers")
    assert len(client.get("/api/retailer/products", headers=as_user(world["oak_login"])).json()) == 1


@pytest.mark.parametrize("pool", [
    dict(deadline_days=1, tiers=tiers((1, 30_000))),                           # Tier price exactly at the Floor
    dict(deadline_days=30, tiers=tiers((5, 1_000), (10, 2_000), (15, 3_000))),  # 3 Tiers, 30 days
])
def test_pools_at_the_edges_of_the_rules_are_accepted(client, world, pool):
    r = client.post("/api/retailer/products", json=public_body(pool=pool), headers=as_user(world["oak_login"]))
    assert r.status_code == 200, r.text


def test_public_product_without_a_pool_is_refused(client, world):
    r = client.post("/api/retailer/products", json=public_body(pool=None), headers=as_user(world["oak_login"]))
    assert_error(r, 400, "invalid_request")


def test_floor_price_above_list_price_is_refused(client, world):
    body = public_body(floor_price_cents=120_000)
    r = client.post("/api/retailer/products", json=body, headers=as_user(world["oak_login"]))
    assert_error(r, 400, "invalid_request")


# --- PATCH /retailer/products/{id} ---------------------------------------------

def test_retailer_edits_only_the_fields_sent(client, world):
    pid = world["table"].id
    r = client.patch(f"/api/retailer/products/{pid}", json={"name": "Walnut Table XL", "demand_threshold": 5},
                     headers=as_user(world["oak_login"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Walnut Table XL"
    assert body["demand"]["threshold"] == 5
    assert body["list_price_cents"] == 150_000
    assert body["category"] == "table"


def test_retailer_cannot_edit_another_retailers_product(client, world):
    r = client.patch(f"/api/retailer/products/{world['chair'].id}", json={"name": "Mine now"},
                     headers=as_user(world["oak_login"]))
    assert_error(r, 404, "not_found")


def test_unknown_product_is_not_found(client, world):
    r = client.patch("/api/retailer/products/999", json={"name": "x"}, headers=as_user(world["oak_login"]))
    assert_error(r, 404, "not_found")


def test_editing_prices_that_push_a_running_pools_tiers_below_the_floor_is_refused(client, world):
    created = client.post("/api/retailer/products", json=public_body(), headers=as_user(world["oak_login"])).json()
    # Tier 2 is 25_000 off 100_000 = 75_000; a Floor Price of 80_000 breaks it.
    r = client.patch(f"/api/retailer/products/{created['id']}", json={"floor_price_cents": 80_000},
                     headers=as_user(world["oak_login"]))
    assert_error(r, 400, "invalid_tiers")
    ok = client.patch(f"/api/retailer/products/{created['id']}", json={"floor_price_cents": 75_000},
                      headers=as_user(world["oak_login"]))
    assert ok.status_code == 200, ok.text
    assert ok.json()["floor_price_cents"] == 75_000


def _pool_with_members(session, world):
    """A locked Pool on Oak's table: Bob charged then refunded 5_000, Carol charged, Dan left."""
    table = world["table"]
    table.visibility = "public"
    session.add(table)
    pool = Pool(product_id=table.id, status="locked", opened_at=T0, deadline=T0 + timedelta(days=7),
                locked_at=T0)
    session.add(pool)
    session.commit()
    session.add_all([Tier(pool_id=pool.id, ordinal=1, min_participants=2, discount_cents=20_000),
                     Tier(pool_id=pool.id, ordinal=2, min_participants=10, discount_cents=30_000)])
    bob, carol, dan = (User(name=n, role="shopper", card_label="Visa") for n in ("Bob", "Carol", "Dan"))
    session.add_all([bob, carol, dan])
    session.commit()
    session.add_all([
        PoolMember(pool_id=pool.id, user_id=bob.id, status="charged", joined_at=T0,
                   charged_cents=130_000, refunded_cents=5_000),
        PoolMember(pool_id=pool.id, user_id=carol.id, status="charged", joined_at=T0 + timedelta(hours=1),
                   charged_cents=130_000),
        PoolMember(pool_id=pool.id, user_id=dan.id, status="left", joined_at=T0 + timedelta(hours=2)),
    ])
    session.commit()
    return pool


def test_retailer_sees_a_pools_members_and_revenue(client, session, world):
    pool = _pool_with_members(session, world)
    r = client.get(f"/api/retailer/pools/{pool.id}", headers=as_user(world["oak_login"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == pool.id
    assert body["status"] == "locked"
    assert body["participants"] == 2
    assert body["my_membership"] is None
    assert "final_price_cents" in body and "description" in body["product"]
    assert body["members"] == [
        {"name": "Bob", "status": "charged", "charged_cents": 130_000, "refunded_cents": 5_000,
         "joined_at": "2026-10-17T12:00:00Z"},
        {"name": "Carol", "status": "charged", "charged_cents": 130_000, "refunded_cents": 0,
         "joined_at": "2026-10-17T13:00:00Z"},
        {"name": "Dan", "status": "left", "charged_cents": 0, "refunded_cents": 0,
         "joined_at": "2026-10-17T14:00:00Z"},
    ]
    assert body["revenue_cents"] == 255_000  # charges minus Tier Refunds


def test_retailer_cannot_see_another_retailers_pool(client, session, world):
    pool = _pool_with_members(session, world)
    r = client.get(f"/api/retailer/pools/{pool.id}", headers=as_user(world["nord_login"]))
    assert_error(r, 404, "not_found")


def test_unknown_pool_is_not_found(client, world):
    assert_error(client.get("/api/retailer/pools/999", headers=as_user(world["oak_login"])), 404, "not_found")


def test_hidden_listing_cannot_be_made_public_by_patch(client, world):
    r = client.patch(f"/api/retailer/products/{world['table'].id}", json={"visibility": "public"},
                     headers=as_user(world["oak_login"]))
    assert_error(r, 400, "invalid_request")
