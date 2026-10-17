"""Join and Leave a Pool (SPEC §4). Every Join and Leave ends by calling `pool_engine.evaluate_pool`.

Errors are raised in the SPEC §3 shape: 402 for `card_required`, 409 for every conflict with the
Pool's or Member's current state.
"""

from fastapi import HTTPException
from sqlmodel import Session, select

from app.errors import api_error
from app.models import Pool, PoolMember, User
from app.services import clock, payments, pool_engine

JOINABLE = ("open", "locked")
SIMULATED_NAME = "Simulated Shopper"


class CardDeclined(HTTPException):
    """Join on a locked Pool whose immediate charge was declined. The Member is left `payment_failed`."""

    def __init__(self):
        super().__init__(402, {"code": "card_required",
                               "message": "Your card was declined. Save a different card and join again"})


def _find_member(session: Session, pool: Pool, user: User) -> PoolMember | None:
    return session.exec(
        select(PoolMember).where(PoolMember.pool_id == pool.id, PoolMember.user_id == user.id)
    ).first()


def join(session: Session, pool: Pool, user: User) -> Pool:
    """Make `user` a pending Member of `pool`, reusing their old row if they left or their card failed."""
    pool = pool_engine.evaluate_pool(session, pool)  # catch up on a passed deadline first
    if pool.status not in JOINABLE:
        raise api_error(409, "pool_not_joinable", f"This Pool is {pool.status} and can't be joined")
    member = _find_member(session, pool, user)
    if member is not None and member.status in pool_engine.ACTIVE:
        raise api_error(409, "already_member", "You're already in this Pool")
    if pool.stock_cap and pool_engine.active_count(session, pool) >= pool.stock_cap:
        raise api_error(409, "stock_cap_reached", "This Pool has reached its stock cap")
    if not payments.has_usable_card(user):
        raise api_error(402, "card_required", "Save a card before joining a Pool")

    if member is None:
        member = PoolMember(pool_id=pool.id, user_id=user.id)
    member.status = "pending"
    member.joined_at = clock.now(session)
    session.add(member)
    session.commit()
    # On a locked Pool, evaluate_pool charges the new pending Member now at the current Tier price (SPEC §4).
    pool = pool_engine.evaluate_pool(session, pool)
    session.refresh(member)
    if member.status == "payment_failed":
        raise CardDeclined()
    return pool


def leave(session: Session, pool: Pool, user: User) -> Pool:
    """Mark `user`'s membership `left`. Only an open Pool can be left; Members of a locked Pool are charged."""
    pool = pool_engine.evaluate_pool(session, pool)
    member = _find_member(session, pool, user)
    if member is None or member.status not in pool_engine.ACTIVE:
        raise api_error(409, "not_member", "You're not in this Pool")
    if pool.status != "open":
        raise api_error(409, "cannot_leave_locked", f"This Pool is {pool.status}, so you can't leave it")
    member.status = "left"
    session.add(member)
    session.commit()
    return pool_engine.evaluate_pool(session, pool)


def simulate_joins(session: Session, pool: Pool, count: int, include_declining_card: bool = False) -> Pool:
    """Demo panel: Join `count` Simulated Shoppers with working cards, plus one with a declining card if asked.

    The declining Simulated Shopper joins first, so on an open Pool it is part of the Lock batch and ends
    `payment_failed` there; on a locked Pool its immediate charge is declined. Simulated Shoppers are
    created when the seeded ones run out. Joining stops early once the Pool can't take more Members.
    """
    joiners = []
    if include_declining_card:
        joiners += _simulated_shoppers(session, pool, 1, declining=True)
    joiners += _simulated_shoppers(session, pool, count, declining=False)
    for user in joiners:
        try:
            pool = join(session, pool, user)
        except CardDeclined:
            continue  # a declined card only drops that Member
        except HTTPException:
            break  # the Pool can't take more Members
    return pool_engine.evaluate_pool(session, pool)


def _simulated_shoppers(session: Session, pool: Pool, count: int, *, declining: bool) -> list[User]:
    """`count` card-saved Simulated Shoppers who aren't active Members of `pool`, creating any that are missing."""
    active = select(PoolMember.user_id).where(PoolMember.pool_id == pool.id,
                                              PoolMember.status.in_(pool_engine.ACTIVE))
    users = list(session.exec(
        select(User)
        .where(User.is_simulated == True, User.card_label != None,  # noqa: E711,E712
               User.card_declines == declining, User.id.not_in(active))
        .order_by(User.id)
        .limit(count)
    ).all())
    number = _last_simulated_number(session)
    while len(users) < count:
        number += 1
        user = User(name=f"{SIMULATED_NAME} {number}", role="shopper", is_simulated=True,
                    card_label=payments.DECLINING_CARD_LABEL if declining else payments.WORKING_CARD_LABEL,
                    card_declines=declining)
        session.add(user)
        session.commit()
        users.append(user)
    return users


def _last_simulated_number(session: Session) -> int:
    """The highest N among users named `Simulated Shopper N`, so new ones get free names."""
    names = session.exec(select(User.name).where(User.name.startswith(f"{SIMULATED_NAME} "))).all()
    numbers = [int(n.rsplit(" ", 1)[1]) for n in names if n.rsplit(" ", 1)[1].isdigit()]
    return max(numbers, default=0)
