"""Ticket #13: Settlement, Tier Refunds, Failed Pools, and the demo clock controls (SPEC §4, §8)."""

from datetime import timedelta

import pytest
from sqlmodel import select

from app.models import Notification, Payment, Pool, PoolMember, Product, Retailer, Tier, User

from tests.conftest import T0, assert_error


@pytest.fixture
def world(session):
    """Oak & Co. (with a retailer login), 6 card-saved Simulated Shoppers, and two open Pools on a
    $1,000 table, Tier 1 at 3 ($100 off) and Tier 2 at 5 ($150 off): `pool` ends in 14 days, `later` in 20."""
    oak = Retailer(name="Oak & Co.")
    session.add(oak)
    session.commit()
    owner = User(name="Oak Admin", role="retailer", retailer_id=oak.id)
    sims = [User(name=f"Sim {i}", role="shopper", is_simulated=True, card_label="Visa •••• 4242")
            for i in range(6)]
    session.add_all([owner, *sims])
    table = Product(retailer_id=oak.id, name="Walnut Table", category="dining_table", list_price_cents=100_000,
                    floor_price_cents=50_000, visibility="public", created_at=T0)
    session.add(table)
    session.commit()
    pools = []
    for days in (14, 20):
        pool = Pool(product_id=table.id, opened_at=T0, deadline=T0 + timedelta(days=days))
        session.add(pool)
        session.commit()
        session.add_all([
            Tier(pool_id=pool.id, ordinal=1, min_participants=3, discount_cents=10_000),
            Tier(pool_id=pool.id, ordinal=2, min_participants=5, discount_cents=15_000),
        ])
        session.commit()
        pools.append(pool)
    return dict(owner=owner, pool=pools[0], later=pools[1])


def simulate(client, pool_id, count):
    r = client.post(f"/api/demo/pools/{pool_id}/simulate-joins", json={"count": count})
    assert r.status_code == 200, r.text
    return r.json()


def advance(client, **body):
    return client.post("/api/demo/clock/advance", json=body)


def detail(client, pool_id):
    return client.get(f"/api/pools/{pool_id}").json()


def payments_of(session, kind):
    return sorted(p.amount_cents for p in session.exec(select(Payment).where(Payment.kind == kind)).all())


# Clock controls


def test_clock_reads_the_sim_clock(client, world):
    r = client.get("/api/demo/clock")
    assert r.status_code == 200, r.text
    assert r.json() == {"now": "2026-10-17T12:00:00Z"}


def test_advancing_by_hours_and_days_moves_the_sim_clock(client, world):
    assert advance(client, hours=5).json() == {"now": "2026-10-17T17:00:00Z"}
    assert advance(client, days=1).json() == {"now": "2026-10-18T17:00:00Z"}
    assert client.get("/api/demo/clock").json() == {"now": "2026-10-18T17:00:00Z"}


def test_jumping_to_a_pools_deadline_sets_the_clock_to_it(client, world):
    r = advance(client, to_deadline_of_pool=world["pool"].id)
    assert r.status_code == 200, r.text
    assert r.json() == {"now": "2026-10-31T12:00:00Z"}


def test_jumping_to_an_unknown_pools_deadline_is_not_found(client, world):
    assert_error(advance(client, to_deadline_of_pool=9999), 404, "not_found")
    assert client.get("/api/demo/clock").json() == {"now": "2026-10-17T12:00:00Z"}


def test_advancing_before_the_deadline_settles_nothing(client, session, world):
    simulate(client, world["pool"].id, 3)
    advance(client, days=13)
    assert detail(client, world["pool"].id)["status"] == "locked"
    assert detail(client, world["later"].id)["status"] == "open"
    assert payments_of(session, "refund") == []


# Settlement


def test_locked_pool_completes_at_its_deadline_with_no_refunds_when_no_higher_tier_was_reached(
        client, session, world):
    pool_id = world["pool"].id
    simulate(client, pool_id, 3)
    advance(client, to_deadline_of_pool=pool_id)
    body = detail(client, pool_id)
    assert (body["status"], body["final_price_cents"]) == ("completed", 90_000)
    assert payments_of(session, "refund") == []
    kinds = [n.kind for n in session.exec(select(Notification)).all()]
    assert kinds.count("pool_completed") == 4  # 3 Members + the retailer
    assert "tier_refund" not in kinds


def test_locked_pool_completes_at_the_final_tier_and_refunds_members_who_paid_more(client, session, world):
    pool_id = world["pool"].id
    simulate(client, pool_id, 3)  # Lock at Tier 1: 3 x $900
    simulate(client, pool_id, 2)  # 4th pays $900, 5th reaches Tier 2 at $850
    advance(client, to_deadline_of_pool=pool_id)
    body = detail(client, pool_id)
    assert (body["status"], body["final_price_cents"]) == ("completed", 85_000)
    assert payments_of(session, "refund") == [5_000] * 4
    members = session.exec(select(PoolMember).where(PoolMember.pool_id == pool_id)).all()
    assert all(m.charged_cents - m.refunded_cents == 85_000 for m in members)
    refund_alerts = session.exec(select(Notification).where(Notification.kind == "tier_refund")).all()
    assert len(refund_alerts) == 4


def test_locked_pool_completes_early_when_a_join_fills_its_stock_cap_and_refunds_earlier_members(
        client, session, world):
    pool = world["pool"]
    pool.stock_cap = 5
    session.add(pool)
    session.commit()
    simulate(client, pool.id, 3)
    body = simulate(client, pool.id, 2)  # cap full at Tier 2, well before the Deadline
    assert (body["status"], body["final_price_cents"]) == ("completed", 85_000)
    assert payments_of(session, "refund") == [5_000] * 4
    assert client.get("/api/demo/clock").json() == {"now": "2026-10-17T12:00:00Z"}


def test_open_pool_past_its_deadline_fails_and_charges_nobody(client, session, world):
    pool_id = world["pool"].id
    simulate(client, pool_id, 2)
    advance(client, days=15)
    body = detail(client, pool_id)
    assert (body["status"], body["final_price_cents"]) == ("failed", None)
    assert session.exec(select(Payment)).all() == []
    failed = session.exec(select(Notification).where(Notification.kind == "pool_failed")).all()
    assert len(failed) == 2


def test_advancing_the_clock_evaluates_every_open_and_locked_pool(client, session, world):
    simulate(client, world["pool"].id, 3)  # locked, ends day 14
    simulate(client, world["later"].id, 1)  # open, ends day 20
    advance(client, to_deadline_of_pool=world["later"].id)
    # Read the rows directly: a GET would evaluate the Pool itself and hide a missed evaluation.
    session.expire_all()
    assert session.get(Pool, world["pool"].id).status == "completed"
    assert session.get(Pool, world["later"].id).status == "failed"
