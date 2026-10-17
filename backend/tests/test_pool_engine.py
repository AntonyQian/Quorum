from datetime import datetime, timedelta

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app import models  # noqa: F401  (register tables)
from app.models import Notification, Payment, Pool, PoolMember, Product, Retailer, Tier, User
from app.services import clock, payments, pool_engine

T0 = datetime(2026, 10, 17, 12, 0, 0)


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        clock.set_now(s, T0)
        yield s


def make_pool(session, *, tiers=((3, 10_000), (5, 15_000)), stock_cap=None, days=14) -> Pool:
    retailer = Retailer(name="Oak & Co.")
    session.add(retailer)
    session.commit()
    session.add(User(name="Oak Owner", role="retailer", retailer_id=retailer.id))
    product = Product(
        retailer_id=retailer.id, name="Walnut Table", category="dining_table",
        list_price_cents=100_000, floor_price_cents=60_000, visibility="public", created_at=T0,
    )
    session.add(product)
    session.commit()
    pool = Pool(product_id=product.id, opened_at=T0, deadline=T0 + timedelta(days=days), stock_cap=stock_cap)
    session.add(pool)
    session.commit()
    for i, (minimum, discount) in enumerate(tiers, start=1):
        session.add(Tier(pool_id=pool.id, ordinal=i, min_participants=minimum, discount_cents=discount))
    session.commit()
    return pool


def join(session, pool, name, *, declines=False) -> PoolMember:
    """Add a member the way the Join route will: pending while open, charged at once when locked."""
    user = User(name=name, role="shopper", card_label="Visa •••• 4242", card_declines=declines)
    session.add(user)
    session.commit()
    member = PoolMember(pool_id=pool.id, user_id=user.id, joined_at=clock.now(session))
    session.add(member)
    session.commit()
    return member


def test_open_pool_below_tier_one_stays_open(session):
    pool = make_pool(session)
    join(session, pool, "a")
    join(session, pool, "b")
    pool_engine.evaluate_pool(session, pool)
    assert pool.status == "open"
    assert session.exec(select(Payment)).all() == []


def test_open_to_locked_charges_everyone_at_tier_one_price(session):
    pool = make_pool(session)
    members = [join(session, pool, n) for n in "abc"]
    pool_engine.evaluate_pool(session, pool)
    assert pool.status == "locked"
    assert pool.locked_at == T0
    for m in members:
        session.refresh(m)
        assert (m.status, m.charged_cents) == ("charged", 90_000)
    assert len(session.exec(select(Payment).where(Payment.kind == "charge")).all()) == 3


def test_lock_charges_the_highest_reached_tier_when_members_skip_past_tier_one(session):
    pool = make_pool(session)
    members = [join(session, pool, n) for n in "abcde"]  # 5 pending: Tier 2 already reached
    pool_engine.evaluate_pool(session, pool)
    assert pool.status == "locked"
    for m in members:
        session.refresh(m)
        assert (m.status, m.charged_cents) == ("charged", 85_000)


def test_locked_to_completed_issues_tier_refunds(session):
    pool = make_pool(session)
    members = [join(session, pool, n) for n in "abc"]
    pool_engine.evaluate_pool(session, pool)
    members += [join(session, pool, n) for n in "de"]  # Tier 2 reached (5 members)
    for m in members[3:]:
        user = session.get(User, m.user_id)
        assert payments.charge(session, m, user, 85_000)
        m.status = "charged"
        session.add(m)
    session.commit()

    pool_engine.evaluate_pool(session, pool, T0 + timedelta(days=15))

    assert pool.status == "completed"
    assert pool.final_price_cents == 85_000
    for m in members[:3]:
        session.refresh(m)
        assert m.refunded_cents == 5_000
    for m in members[3:]:
        session.refresh(m)
        assert m.refunded_cents == 0
    refunds = session.exec(select(Payment).where(Payment.kind == "refund")).all()
    assert [r.amount_cents for r in refunds] == [5_000, 5_000, 5_000]


def test_open_to_failed_at_deadline_charges_nobody(session):
    pool = make_pool(session)
    join(session, pool, "a")
    pool_engine.evaluate_pool(session, pool, T0 + timedelta(days=15))
    assert pool.status == "failed"
    assert session.exec(select(Payment)).all() == []
    kinds = [n.kind for n in session.exec(select(Notification)).all()]
    assert "pool_failed" in kinds


def test_declined_card_at_lock_drops_only_that_member(session):
    pool = make_pool(session)
    good = [join(session, pool, n) for n in "ab"]
    bad = join(session, pool, "c", declines=True)
    pool_engine.evaluate_pool(session, pool)
    assert pool.status == "locked"  # still locks even though active count drops below Tier 1
    session.refresh(bad)
    assert (bad.status, bad.charged_cents) == ("payment_failed", 0)
    for m in good:
        session.refresh(m)
        assert m.status == "charged"
    assert pool_engine.active_count(session, pool) == 2
    failed = session.exec(select(Payment).where(Payment.status == "failed")).all()
    assert len(failed) == 1


def test_stock_cap_settles_locked_pool_early(session):
    pool = make_pool(session, stock_cap=3)
    for n in "abc":
        join(session, pool, n)
    pool_engine.evaluate_pool(session, pool)  # locks, then the cap settles it in the same pass
    assert pool.status == "completed"
    assert pool.final_price_cents == 90_000
    assert pool.closed_at == T0
    assert session.exec(select(Payment).where(Payment.kind == "refund")).all() == []
