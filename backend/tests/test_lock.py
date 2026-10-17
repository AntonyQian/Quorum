"""Ticket #12: Lock at Tier 1, and the demo panel's simulate-joins (SPEC §4, §8)."""

from datetime import timedelta

import pytest
from sqlmodel import select

from app.models import Notification, Payment, Pool, Product, Retailer, Tier, User

from tests.conftest import T0, as_user, assert_error


@pytest.fixture
def world(session):
    """Oak & Co. (with a retailer login), 4 card-saved Simulated Shoppers, one declining Simulated Shopper,
    Bob (a real shopper with a card), and an open table Pool: Tier 1 at 3 ($100 off), Tier 2 at 5 ($150 off)."""
    oak = Retailer(name="Oak & Co.")
    session.add(oak)
    session.commit()
    owner = User(name="Oak Admin", role="retailer", retailer_id=oak.id)
    bob = User(name="Bob", role="shopper", card_label="Visa •••• 4242")
    sims = [User(name=f"Sim {i}", role="shopper", is_simulated=True, card_label="Visa •••• 4242")
            for i in range(4)]
    decliner = User(name="Declining Dee", role="shopper", is_simulated=True, card_label="Visa •••• 0341",
                    card_declines=True)
    session.add_all([owner, bob, *sims, decliner])
    table = Product(retailer_id=oak.id, name="Walnut Table", category="dining_table", list_price_cents=100_000,
                    floor_price_cents=50_000, visibility="public", created_at=T0)
    session.add(table)
    session.commit()
    pool = Pool(product_id=table.id, opened_at=T0, deadline=T0 + timedelta(days=14))
    session.add(pool)
    session.commit()
    session.add_all([
        Tier(pool_id=pool.id, ordinal=1, min_participants=3, discount_cents=10_000),
        Tier(pool_id=pool.id, ordinal=2, min_participants=5, discount_cents=15_000),
    ])
    session.commit()
    return dict(owner=owner, bob=bob, sims=sims, decliner=decliner, pool=pool)


def simulate(client, pool_id, **body):
    return client.post(f"/api/demo/pools/{pool_id}/simulate-joins", json=body)


def test_simulated_joins_below_tier_one_add_pending_members(client, session, world):
    r = simulate(client, world["pool"].id, count=2)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["status"], body["participants"], body["my_membership"]) == ("open", 2, None)
    assert session.exec(select(Payment)).all() == []


def test_simulated_joins_reaching_tier_one_lock_the_pool_and_charge_every_member(client, session, world):
    r = simulate(client, world["pool"].id, count=3)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["status"], body["participants"], body["current_price_cents"]) == ("locked", 3, 90_000)
    charges = session.exec(select(Payment).where(Payment.kind == "charge")).all()
    assert sorted((c.amount_cents, c.status) for c in charges) == [(90_000, "succeeded")] * 3
    retailer_alerts = session.exec(select(Notification).where(Notification.user_id == world["owner"].id)).all()
    assert [n.kind for n in retailer_alerts] == ["pool_locked"]


def test_declining_simulated_shopper_ends_payment_failed_and_the_pool_still_locks(client, session, world):
    r = simulate(client, world["pool"].id, count=2, include_declining_card=True)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["status"], body["participants"]) == ("locked", 2)  # Locks even though 2 < Tier 1
    dee = world["decliner"]
    detail = client.get(f"/api/pools/{world['pool'].id}", headers=as_user(dee)).json()
    assert detail["my_membership"] == {"status": "payment_failed", "charged_cents": 0, "refunded_cents": 0}
    failed = session.exec(select(Payment).where(Payment.status == "failed")).one()
    assert (failed.kind, failed.amount_cents) == ("charge", 90_000)
    kinds = [n.kind for n in session.exec(select(Notification).where(Notification.user_id == dee.id)).all()]
    assert kinds == ["payment_failed"]


def test_simulated_joins_on_a_locked_pool_are_charged_immediately_at_the_current_tier(client, session, world):
    pool_id = world["pool"].id
    simulate(client, pool_id, count=3)  # Lock at Tier 1: 3 x $900
    r = simulate(client, pool_id, count=2)  # 4th pays Tier 1 ($900), 5th reaches Tier 2 ($850)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["status"], body["participants"], body["current_price_cents"]) == ("locked", 5, 85_000)
    amounts = [p.amount_cents for p in session.exec(select(Payment).order_by(Payment.id)).all()]
    assert amounts == [90_000, 90_000, 90_000, 90_000, 85_000]


def test_declining_card_on_a_locked_pool_is_dropped_without_failing_the_request(client, session, world):
    pool_id = world["pool"].id
    simulate(client, pool_id, count=3)
    r = simulate(client, pool_id, count=1, include_declining_card=True)
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["participants"]) == ("locked", 4)
    assert len(session.exec(select(Payment).where(Payment.status == "failed")).all()) == 1


def test_simulate_joins_creates_simulated_shoppers_when_the_seeded_ones_run_out(client, session, world):
    r = simulate(client, world["pool"].id, count=6)  # only 4 card-saved sims exist
    assert r.status_code == 200, r.text
    assert r.json()["participants"] == 6
    sims = session.exec(select(User).where(User.is_simulated == True)).all()  # noqa: E712
    assert len(sims) == 7  # 4 + 1 declining + 2 new


def test_simulate_joins_never_uses_real_shoppers(client, session, world):
    simulate(client, world["pool"].id, count=4)
    detail = client.get(f"/api/pools/{world['pool'].id}", headers=as_user(world["bob"])).json()
    assert detail["my_membership"] is None


def test_simulate_joins_stops_at_the_stock_cap(client, session, world):
    pool = world["pool"]
    pool.stock_cap = 4
    session.add(pool)
    session.commit()
    r = simulate(client, pool.id, count=6)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["status"], body["participants"]) == ("completed", 4)


def test_simulate_joins_on_an_unknown_pool_is_not_found(client, world):
    assert_error(simulate(client, 9999, count=1), 404, "not_found")


@pytest.mark.parametrize("body", [{}, {"count": -1}])
def test_simulate_joins_with_a_bad_body_is_invalid_request(client, world, body):
    assert_error(simulate(client, world["pool"].id, **body), 422, "invalid_request")
