"""Pool state machine (SPEC §4). `evaluate_pool` is the only place a Pool's status changes."""

from datetime import datetime

from sqlmodel import Session, select

from app.models import Pool, PoolMember, Product, Tier, User
from app.services import clock, payments
from app.services.notifications import notify, notify_retailer

ACTIVE = ("pending", "charged")


def get_tiers(session: Session, pool: Pool) -> list[Tier]:
    return list(session.exec(select(Tier).where(Tier.pool_id == pool.id).order_by(Tier.ordinal)).all())


def get_members(session: Session, pool: Pool, statuses: tuple[str, ...] = ACTIVE) -> list[PoolMember]:
    return list(
        session.exec(
            select(PoolMember).where(PoolMember.pool_id == pool.id, PoolMember.status.in_(statuses))
        ).all()
    )


def active_count(session: Session, pool: Pool) -> int:
    return len(get_members(session, pool))


def current_tier(tiers: list[Tier], count: int) -> Tier | None:
    reached = [t for t in tiers if t.min_participants <= count]
    return reached[-1] if reached else None


def next_tier(tiers: list[Tier], count: int) -> Tier | None:
    for t in tiers:
        if t.min_participants > count:
            return t
    return None


def tier_price(product: Product, tier: Tier) -> int:
    return product.list_price_cents - tier.discount_cents


def current_price(product: Product, tiers: list[Tier], count: int) -> int:
    """Current Tier price, or the Tier 1 price when no Tier is reached yet."""
    tier = current_tier(tiers, count) or tiers[0]
    return tier_price(product, tier)


def charge_member(session: Session, member: PoolMember, user: User, price: int) -> str:
    """Charge one Member at `price`: `charged` on success, `payment_failed` on a decline, still `pending` when
    the provider is unavailable (retried on the next evaluation). Returns the charge outcome; does not commit."""
    outcome = payments.charge(session, member, user, price)
    if outcome != payments.UNAVAILABLE:
        member.status = "charged" if outcome == payments.SUCCEEDED else "payment_failed"
        session.add(member)
    return outcome


def _charge_pending(session: Session, pool: Pool, product: Product, price: int, link: str) -> None:
    """Charge every pending Member at `price` and notify the ones whose charge was decided. Commits after each
    charge so a later failure can't lose a charge the provider already made."""
    for m in get_members(session, pool, ("pending",)):
        outcome = charge_member(session, m, session.get(User, m.user_id), price)
        if outcome == payments.SUCCEEDED:
            notify(session, m.user_id, "pool_locked", f"{product.name} pool locked",
                   f"You were charged ${price / 100:,.2f}.", link)
        elif outcome == payments.DECLINED:
            notify(session, m.user_id, "payment_failed", f"Payment failed for {product.name}",
                   "Your card was declined, so you were dropped from the pool.", link)
        session.commit()


def _settle(session: Session, pool: Pool, product: Product, tiers: list[Tier], now: datetime, link: str) -> None:
    """Issue every Tier Refund still owed, then complete the Pool. If a refund fails, the Pool stays locked and
    the next evaluation retries only what is still owed (charged - final - already refunded)."""
    charged = get_members(session, pool, ("charged",))
    final = tier_price(product, current_tier(tiers, len(charged)) or tiers[0])
    all_refunded = True
    for m in charged:
        owed = m.charged_cents - final - m.refunded_cents
        if owed > 0:
            all_refunded &= payments.refund(session, m, owed)
            session.commit()
    if not all_refunded:
        return
    for m in charged:
        if m.refunded_cents > 0:
            notify(session, m.user_id, "tier_refund", f"Tier refund for {product.name}",
                   f"${m.refunded_cents / 100:,.2f} refunded; everyone paid ${final / 100:,.2f}.", link)
        else:
            notify(session, m.user_id, "pool_completed", f"{product.name} pool completed",
                   f"Final price ${final / 100:,.2f}.", link)
    pool.status = "completed"
    pool.closed_at = now
    pool.final_price_cents = final
    notify_retailer(session, product.retailer_id, "pool_completed", f"{product.name} pool completed",
                    f"Final price ${final / 100:,.2f} for {len(charged)} members.", f"/retailer/pools/{pool.id}")


def evaluate_pool(session: Session, pool: Pool, now: datetime | None = None) -> Pool:
    """Apply every pending state transition to the Pool, then commit."""
    now = now or clock.now(session)
    product = session.get(Product, pool.product_id)
    tiers = get_tiers(session, pool)
    link = f"/pools/{pool.id}"

    if pool.status == "open":
        count = active_count(session, pool)
        if count >= tiers[0].min_participants:
            pool.status = "locked"
            pool.locked_at = now
            session.add(pool)
            notify_retailer(session, product.retailer_id, "pool_locked", f"{product.name} pool locked",
                            f"{count} members reached Tier 1.", f"/retailer/pools/{pool.id}")
            _charge_pending(session, pool, product, tier_price(product, current_tier(tiers, count)), link)
        elif now >= pool.deadline:
            pool.status = "failed"
            pool.closed_at = now
            for m in get_members(session, pool):
                notify(session, m.user_id, "pool_failed", f"{product.name} pool didn't reach Tier 1",
                       "You were not charged.", link)

    elif pool.status == "locked":
        # Late joiners, and Members whose charge hit a provider outage, pay the current Tier price.
        _charge_pending(session, pool, product, current_price(product, tiers, active_count(session, pool)), link)

    if pool.status == "locked":
        count = active_count(session, pool)
        unresolved = get_members(session, pool, ("pending",))
        if not unresolved and (now >= pool.deadline or (pool.stock_cap and count >= pool.stock_cap)):
            _settle(session, pool, product, tiers, now, link)

    session.add(pool)
    session.commit()
    session.refresh(pool)
    return pool


def evaluate_all(session: Session, now: datetime | None = None) -> None:
    """Evaluate every open or locked Pool (used after the Sim Clock advances)."""
    pools = session.exec(select(Pool).where(Pool.status.in_(("open", "locked")))).all()
    for pool in pools:
        evaluate_pool(session, pool, now)
