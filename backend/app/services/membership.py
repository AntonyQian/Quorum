"""Join and Leave a Pool (SPEC §4). Every Join and Leave ends by calling `pool_engine.evaluate_pool`.

Errors are raised in the SPEC §3 shape: 402 for `card_required`, 409 for every conflict with the
Pool's or Member's current state.
"""

from sqlmodel import Session, select

from app.errors import api_error
from app.models import Pool, PoolMember, Product, User
from app.services import clock, payments, pool_engine

JOINABLE = ("open", "locked")


def _membership(session: Session, pool: Pool, user: User) -> PoolMember | None:
    return session.exec(
        select(PoolMember).where(PoolMember.pool_id == pool.id, PoolMember.user_id == user.id)
    ).first()


def join(session: Session, pool: Pool, user: User) -> Pool:
    """Make `user` a pending Member of `pool`, reusing their old row if they left or their card failed."""
    pool = pool_engine.evaluate_pool(session, pool)  # catch up on a passed deadline first
    if pool.status not in JOINABLE:
        raise api_error(409, "pool_not_joinable", f"This Pool is {pool.status} and can't be joined")
    member = _membership(session, pool, user)
    if member is not None and member.status in pool_engine.ACTIVE:
        raise api_error(409, "already_member", "You're already in this Pool")
    if not user.card_label:
        raise api_error(402, "card_required", "Save a card before joining a Pool")
    if pool.stock_cap and pool_engine.active_count(session, pool) >= pool.stock_cap:
        raise api_error(409, "stock_cap_reached", "This Pool has reached its stock cap")

    if member is None:
        member = PoolMember(pool_id=pool.id, user_id=user.id, joined_at=clock.now(session))
    member.status = "pending"
    member.joined_at = clock.now(session)
    session.add(member)
    session.commit()
    if pool.status == "locked" and not _charge_late_joiner(session, pool, member, user):
        pool_engine.evaluate_pool(session, pool)
        raise api_error(402, "card_required", "Your card was declined. Save a different card and join again")
    return pool_engine.evaluate_pool(session, pool)


def _charge_late_joiner(session: Session, pool: Pool, member: PoolMember, user: User) -> bool:
    """Join on a locked Pool: charge now at the current Tier price, counting the new Member (SPEC §4)."""
    product = session.get(Product, pool.product_id)
    tiers = pool_engine.get_tiers(session, pool)
    price = pool_engine.current_price(product, tiers, pool_engine.active_count(session, pool))
    ok = payments.charge(session, member, user, price)
    member.status = "charged" if ok else "payment_failed"
    session.add(member)
    session.commit()
    return ok


def leave(session: Session, pool: Pool, user: User) -> Pool:
    """Mark `user`'s membership `left`. Only an open Pool can be left; Members of a locked Pool are charged."""
    pool = pool_engine.evaluate_pool(session, pool)
    member = _membership(session, pool, user)
    if member is None or member.status not in pool_engine.ACTIVE:
        raise api_error(409, "not_member", "You're not in this Pool")
    if pool.status != "open":
        raise api_error(409, "cannot_leave_locked", f"This Pool is {pool.status}, so you can't leave it")
    member.status = "left"
    session.add(member)
    session.commit()
    return pool_engine.evaluate_pool(session, pool)
