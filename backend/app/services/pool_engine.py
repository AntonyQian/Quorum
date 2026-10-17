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
            price = tier_price(product, current_tier(tiers, count))
            for m in get_members(session, pool, ("pending",)):
                user = session.get(User, m.user_id)
                if payments.charge(session, m, user, price):
                    m.status = "charged"
                    notify(session, m.user_id, "pool_locked", f"{product.name} pool locked",
                           f"You were charged ${price / 100:,.2f}.", link)
                else:
                    m.status = "payment_failed"
                    notify(session, m.user_id, "payment_failed", f"Payment failed for {product.name}",
                           "Your card was declined, so you were dropped from the pool.", link)
                session.add(m)
            notify_retailer(session, product.retailer_id, "pool_locked", f"{product.name} pool locked",
                            f"{count} members reached Tier 1.", f"/retailer/pools/{pool.id}")
        elif now >= pool.deadline:
            pool.status = "failed"
            pool.closed_at = now
            for m in get_members(session, pool):
                notify(session, m.user_id, "pool_failed", f"{product.name} pool didn't reach Tier 1",
                       "You were not charged.", link)

    if pool.status == "locked":
        count = active_count(session, pool)
        if now >= pool.deadline or (pool.stock_cap and count >= pool.stock_cap):
            charged = get_members(session, pool, ("charged",))
            final = tier_price(product, current_tier(tiers, len(charged)) or tiers[0])
            for m in charged:
                diff = m.charged_cents - final
                if diff > 0:
                    payments.refund(session, m, diff)
                    notify(session, m.user_id, "tier_refund", f"Tier refund for {product.name}",
                           f"${diff / 100:,.2f} refunded; everyone paid ${final / 100:,.2f}.", link)
                else:
                    notify(session, m.user_id, "pool_completed", f"{product.name} pool completed",
                           f"Final price ${final / 100:,.2f}.", link)
            pool.status = "completed"
            pool.closed_at = now
            pool.final_price_cents = final
            notify_retailer(session, product.retailer_id, "pool_completed", f"{product.name} pool completed",
                            f"Final price ${final / 100:,.2f} for {len(charged)} members.",
                            f"/retailer/pools/{pool.id}")

    session.add(pool)
    session.commit()
    session.refresh(pool)
    return pool


def evaluate_all(session: Session, now: datetime | None = None) -> None:
    """Evaluate every open or locked Pool (used after the Sim Clock advances)."""
    pools = session.exec(select(Pool).where(Pool.status.in_(("open", "locked")))).all()
    for pool in pools:
        evaluate_pool(session, pool, now)
