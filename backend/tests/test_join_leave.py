"""Ticket #11: mock card saving, Join and Leave (SPEC §4, §5, §8)."""

from datetime import timedelta

import pytest
from sqlmodel import select

from app import config
from app.models import Payment, Pool, PoolMember, Product, Retailer, Tier, User
from app.services import clock

from tests.conftest import T0
from tests.test_read_endpoints import as_user, assert_error


@pytest.fixture
def world(session):
    """Alice (no card), Bob (card), a declining-card shopper, sims, and an open sofa Pool (Tier 1 at 3)."""
    oak = Retailer(name="Oak & Co.")
    session.add(oak)
    session.commit()
    alice = User(name="Alice", role="shopper")
    bob = User(name="Bob", role="shopper", card_label="Visa •••• 4242")
    decliner = User(name="Dee", role="shopper", card_label="Visa •••• 0341", card_declines=True)
    sims = [User(name=f"Sim {i}", role="shopper", is_simulated=True, card_label="Visa •••• 4242")
            for i in range(6)]
    session.add_all([alice, bob, decliner, *sims])
    sofa = Product(retailer_id=oak.id, name="Walnut Sofa", category="sofa", list_price_cents=100_000,
                   floor_price_cents=50_000, visibility="public", created_at=T0)
    session.add(sofa)
    session.commit()
    pool = Pool(product_id=sofa.id, opened_at=T0, deadline=T0 + timedelta(days=3))
    session.add(pool)
    session.commit()
    session.add_all([
        Tier(pool_id=pool.id, ordinal=1, min_participants=3, discount_cents=10_000),
        Tier(pool_id=pool.id, ordinal=2, min_participants=5, discount_cents=15_000),
    ])
    session.commit()
    return dict(alice=alice, bob=bob, decliner=decliner, sims=sims, pool=pool)


def join(client, pool, user):
    return client.post(f"/api/pools/{pool.id}/join", headers=as_user(user))


def leave(client, pool, user):
    return client.post(f"/api/pools/{pool.id}/leave", headers=as_user(user))


# --- mock card saving --------------------------------------------------------

def test_setup_session_returns_the_mock_success_url(client, world):
    alice = world["alice"]
    r = client.post("/api/payments/setup-session", json={"return_to": "/pools/1"}, headers=as_user(alice))
    assert r.status_code == 200, r.text
    assert r.json() == {"url": f"{config.FRONTEND_URL}/payment/success?session_id=mock_{alice.id}"}


def test_confirm_setup_stores_a_card_label_on_the_user(client, world):
    alice = world["alice"]
    r = client.post("/api/payments/confirm-setup", json={"session_id": f"mock_{alice.id}"}, headers=as_user(alice))
    assert r.status_code == 200, r.text
    assert r.json() == {"card_label": "Visa •••• 4242"}
    assert client.get("/api/me", headers=as_user(alice)).json()["card_label"] == "Visa •••• 4242"


@pytest.mark.parametrize("path,body", [("setup-session", {}), ("confirm-setup", {"session_id": "mock_1"})])
def test_payment_endpoints_need_a_user(client, world, path, body):
    assert_error(client.post(f"/api/payments/{path}", json=body), 401, "forbidden")


# --- join --------------------------------------------------------------------

def test_join_open_pool_makes_a_pending_member_without_charging(client, session, world):
    r = join(client, world["pool"], world["bob"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["participants"] == 1
    assert body["status"] == "open"
    assert body["my_membership"] == {"status": "pending", "charged_cents": 0, "refunded_cents": 0}
    assert session.exec(select(Payment)).all() == []


def test_join_without_a_saved_card_is_card_required(client, world):
    assert_error(join(client, world["pool"], world["alice"]), 402, "card_required")


def test_join_after_saving_a_card_succeeds(client, world):
    alice = world["alice"]
    client.post("/api/payments/confirm-setup", json={"session_id": f"mock_{alice.id}"}, headers=as_user(alice))
    r = join(client, world["pool"], alice)
    assert r.status_code == 200, r.text
    assert r.json()["my_membership"]["status"] == "pending"


def test_join_twice_is_already_member(client, world):
    join(client, world["pool"], world["bob"])
    assert_error(join(client, world["pool"], world["bob"]), 409, "already_member")


def test_join_unknown_pool_is_not_found(client, world):
    assert_error(client.post("/api/pools/9999/join", headers=as_user(world["bob"])), 404, "not_found")


def test_join_needs_a_user(client, world):
    assert_error(client.post(f"/api/pools/{world['pool'].id}/join"), 401, "forbidden")


@pytest.mark.parametrize("status", ["completed", "failed"])
def test_join_closed_pool_is_pool_not_joinable(client, session, world, status):
    pool = world["pool"]
    pool.status = status
    session.add(pool)
    session.commit()
    assert_error(join(client, pool, world["bob"]), 409, "pool_not_joinable")


def test_join_after_the_deadline_passed_is_pool_not_joinable(client, session, world):
    clock.set_now(session, T0 + timedelta(days=4))
    assert_error(join(client, world["pool"], world["bob"]), 409, "pool_not_joinable")


def test_join_when_stock_cap_is_full_is_stock_cap_reached(client, session, world):
    pool = world["pool"]
    pool.stock_cap = 2
    session.add(pool)
    session.commit()
    join(client, pool, world["sims"][0])
    join(client, pool, world["sims"][1])
    assert_error(join(client, pool, world["bob"]), 409, "stock_cap_reached")


# --- leave and re-join -------------------------------------------------------

def test_leave_open_pool_marks_the_member_left(client, world):
    join(client, world["pool"], world["bob"])
    r = leave(client, world["pool"], world["bob"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["participants"] == 0
    assert body["my_membership"]["status"] == "left"


def test_rejoin_after_leaving_reuses_the_membership_row(client, session, world):
    pool, bob = world["pool"], world["bob"]
    join(client, pool, bob)
    leave(client, pool, bob)
    r = join(client, pool, bob)
    assert r.status_code == 200, r.text
    assert r.json()["my_membership"]["status"] == "pending"
    rows = session.exec(select(PoolMember).where(PoolMember.pool_id == pool.id,
                                                 PoolMember.user_id == bob.id)).all()
    assert len(rows) == 1


@pytest.mark.parametrize("left_first", [False, True])
def test_leave_without_an_active_membership_is_not_member(client, world, left_first):
    if left_first:
        join(client, world["pool"], world["bob"])
        leave(client, world["pool"], world["bob"])
    assert_error(leave(client, world["pool"], world["bob"]), 409, "not_member")


def test_leave_unknown_pool_is_not_found(client, world):
    assert_error(client.post("/api/pools/9999/leave", headers=as_user(world["bob"])), 404, "not_found")


def test_leave_locked_pool_is_cannot_leave_locked(client, world):
    pool = world["pool"]
    for sim in world["sims"][:2]:
        join(client, pool, sim)
    join(client, pool, world["bob"])  # third member reaches Tier 1: Lock
    assert_error(leave(client, pool, world["bob"]), 409, "cannot_leave_locked")


# --- join on a locked Pool ----------------------------------------------------

def lock_with(client, pool, users):
    for u in users:
        join(client, pool, u)


def test_join_locked_pool_charges_now_at_the_tier_price_after_counting_the_new_member(client, session, world):
    pool = world["pool"]
    lock_with(client, pool, world["sims"][:4])  # locked at Tier 1 with 4 members
    r = join(client, pool, world["bob"])  # 5th member reaches Tier 2: $1000 - $150
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "locked"
    assert body["participants"] == 5
    assert body["my_membership"] == {"status": "charged", "charged_cents": 85_000, "refunded_cents": 0}
    charge = session.exec(select(Payment).where(Payment.amount_cents == 85_000)).one()
    assert (charge.kind, charge.status) == ("charge", "succeeded")


def test_join_locked_pool_with_a_declined_card_is_card_required_and_marks_payment_failed(client, session, world):
    pool, dee = world["pool"], world["decliner"]
    lock_with(client, pool, world["sims"][:3])
    assert_error(join(client, pool, dee), 402, "card_required")
    detail = client.get(f"/api/pools/{pool.id}", headers=as_user(dee)).json()
    assert detail["participants"] == 3
    assert detail["my_membership"]["status"] == "payment_failed"
    failed = session.exec(select(Payment).where(Payment.status == "failed")).one()
    assert failed.amount_cents == 90_000


def test_payment_failed_member_can_rejoin_with_a_working_card_on_the_same_row(client, session, world):
    pool, dee = world["pool"], world["decliner"]
    lock_with(client, pool, world["sims"][:3])
    join(client, pool, dee)
    dee_row = session.get(User, dee.id)
    dee_row.card_declines = False  # Dee saved a working card
    session.add(dee_row)
    session.commit()
    r = join(client, pool, dee)
    assert r.status_code == 200, r.text
    assert r.json()["my_membership"]["status"] == "charged"
    rows = session.exec(select(PoolMember).where(PoolMember.pool_id == pool.id,
                                                 PoolMember.user_id == dee.id)).all()
    assert len(rows) == 1
