"""Tell Shoppers when a Pool opens that fits a Wish they made before it existed (SPEC §6)."""

from sqlmodel import Session, select

from app.models import DemandHit, Pool, Product, User, Wish
from app.services import notifications, pool_engine
from app.services.wish_constraints import categories_compatible, product_has_terms, required_terms


def wish_fits(wish: Wish, product: Product, best_price_cents: int) -> bool:
    """A Wish fits when it names a category or a material/color (a vaguer one would match everything), the
    Product is in that category with every named material or color, and the budget, if any, reaches the Pool's
    best Tier price."""
    parsed = wish.parsed or {}
    category = parsed.get("category")
    terms = required_terms(wish.text)
    if not category and not terms:
        return False
    if category and not categories_compatible(category, product.category):
        return False
    if terms and not product_has_terms(product, terms):
        return False
    budget = parsed.get("budget_max_cents")
    return budget is None or best_price_cents <= budget


def notify_matching_wishes(session: Session, pool: Pool, product: Product) -> int:
    """Send a `wish_pool_opened` notification to each Shopper whose earlier Wish fits the newly opened Pool, once per
    Shopper. Shoppers with a Demand Hit on the Product already get the launch notification. The caller commits."""
    tiers = pool_engine.get_tiers(session, pool)
    best_price = product.list_price_cents - max((t.discount_cents for t in tiers), default=0)
    already = set(session.exec(select(DemandHit.user_id).where(DemandHit.product_id == product.id)).all())
    wishes = session.exec(
        select(Wish).join(User, User.id == Wish.user_id)
        .where(Wish.created_at <= pool.opened_at, User.role == "shopper", User.is_simulated == False)  # noqa: E712
        .order_by(Wish.id.desc())
    ).all()
    sent: set[int] = set()
    for wish in wishes:
        if wish.user_id in sent or wish.user_id in already or not wish_fits(wish, product, best_price):
            continue
        sent.add(wish.user_id)
        notifications.notify(
            session, wish.user_id, "wish_pool_opened", f"A Pool opened for your Wish: {product.name}",
            f"You searched for “{wish.text}”. This Pool can drop to ${best_price // 100:,} with enough Members.",
            link=f"/pools/{pool.id}",
        )
    return len(sent)
