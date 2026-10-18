"""Demand Hits on Hidden Listings and the Demand Threshold alert (SPEC §6, ADR 0002)."""

from sqlmodel import Session, func, select

from app.models import DemandHit, Notification, Product, User, Wish
from app.services import clock, notifications


def hit_count(session: Session, product: Product) -> int:
    return session.exec(select(func.count()).select_from(DemandHit).where(DemandHit.product_id == product.id)).one()


def _alert_link(product: Product) -> str:
    return f"/retailer?product={product.id}"


def check_threshold(session: Session, product: Product) -> None:
    """Alert the retailer once per Product when its hits reach or pass the Demand Threshold. The alert itself
    (a `demand_threshold` notification linking to this Product) is the marker that keeps it to one, so a
    threshold lowered to or below the current count alerts too. The caller commits."""
    if product.visibility != "hidden" or product.demand_threshold is None:
        return
    count = hit_count(session, product)
    if count < product.demand_threshold:
        return
    alerted = session.exec(
        select(Notification.id).where(Notification.kind == "demand_threshold",
                                      Notification.link == _alert_link(product))
    ).first()
    if alerted is not None:
        return
    notifications.notify_retailer(
        session, product.retailer_id, "demand_threshold",
        f"{count} shoppers want something like {product.name}. Launch a pool?",
        "The Demand Threshold for this Hidden Listing has been reached.", link=_alert_link(product),
    )
    session.flush()


def add_demand_hit(session: Session, product: Product, user: User, wish: Wish) -> bool:
    """Record a Demand Hit (at most one per user and Product), then check the Demand Threshold alert.
    Returns False when the user already had a hit. The caller commits."""
    exists = session.exec(
        select(DemandHit.id).where(DemandHit.product_id == product.id, DemandHit.user_id == user.id)
    ).first()
    if exists is not None:
        return False
    session.add(DemandHit(product_id=product.id, user_id=user.id, wish_id=wish.id, created_at=clock.now(session)))
    session.flush()
    check_threshold(session, product)
    return True


def simulate_demand(session: Session, product: Product, count: int) -> int:
    """Add up to `count` Demand Hits from Simulated Shoppers who haven't hit this Product yet, each with a fake
    Wish (no Claude call). Returns the Product's total hits."""
    already = select(DemandHit.user_id).where(DemandHit.product_id == product.id)
    shoppers = session.exec(
        select(User).where(User.is_simulated == True, User.role == "shopper", User.id.not_in(already))  # noqa: E712
        .order_by(User.id).limit(count)
    ).all()
    for shopper in shoppers:
        wish = Wish(user_id=shopper.id, text=f"Looking for something like a {product.name.lower()}",
                    parsed={"category": product.category}, created_at=clock.now(session))
        session.add(wish)
        session.flush()
        add_demand_hit(session, product, shopper, wish)
    session.commit()
    return hit_count(session, product)


def remove_demand(session: Session, product: Product, count: int) -> int:
    """Demo panel: drop the newest `count` Demand Hits from Simulated Shoppers. Returns the Product's total hits."""
    hits = session.exec(
        select(DemandHit).join(User, User.id == DemandHit.user_id)
        .where(DemandHit.product_id == product.id, User.is_simulated == True)  # noqa: E712
        .order_by(DemandHit.id.desc()).limit(count)
    ).all()
    for hit in hits:
        session.delete(hit)
    session.commit()
    return hit_count(session, product)
