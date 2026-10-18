"""Demo panel extras: simulated leaves, removing demand, reset; retailer product delete."""

from app.models import Pool, Product, Retailer, Tier, User

from tests.conftest import T0, as_user


def make_world(session):
    retailer = Retailer(name="Oak & Co.")
    session.add(retailer)
    session.commit()
    login = User(name="Login", role="retailer", retailer_id=retailer.id)
    session.add(login)
    hidden = Product(retailer_id=retailer.id, name="Hidden Desk", category="desk", list_price_cents=100_00,
                     floor_price_cents=50_00, visibility="hidden", demand_threshold=3, created_at=T0)
    live = Product(retailer_id=retailer.id, name="Live Desk", category="desk", list_price_cents=100_00,
                   floor_price_cents=50_00, visibility="public", created_at=T0)
    session.add_all([hidden, live])
    session.commit()
    pool = Pool(product_id=live.id, status="open", opened_at=T0, deadline=T0.replace(day=27))
    session.add(pool)
    session.commit()
    session.add(Tier(pool_id=pool.id, ordinal=1, min_participants=50, discount_cents=10_00))
    session.commit()
    return login, hidden, live, pool


def test_simulate_leaves_lowers_participants(client, session):
    _, _, _, pool = make_world(session)
    assert client.post(f"/api/demo/pools/{pool.id}/simulate-joins", json={"count": 5}).json()["participants"] == 5
    body = client.post(f"/api/demo/pools/{pool.id}/simulate-leaves", json={"count": 2}).json()
    assert body["participants"] == 3


def test_remove_demand_lowers_hits(client, session):
    _, hidden, _, _ = make_world(session)
    session.add_all([User(name=f"Sim {i}", role="shopper", is_simulated=True) for i in range(4)])
    session.commit()
    assert client.post(f"/api/demo/products/{hidden.id}/simulate-demand", json={"count": 4}).json()["total_hits"] == 4
    assert client.post(f"/api/demo/products/{hidden.id}/remove-demand", json={"count": 3}).json()["total_hits"] == 1


def test_delete_product_only_without_members(client, session):
    login, hidden, live, pool = make_world(session)
    assert client.delete(f"/api/retailer/products/{hidden.id}", headers=as_user(login)).status_code == 200
    client.post(f"/api/demo/pools/{pool.id}/simulate-joins", json={"count": 1})
    r = client.delete(f"/api/retailer/products/{live.id}", headers=as_user(login))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "product_in_use"
