"""Build the SPEC §8 response shapes from database rows."""

from datetime import timedelta

from sqlmodel import Session, select

from app.models import DemandHit, Payment, Pool, PoolMember, Product, Retailer, User, Wish
from app.schemas import (
    DemandSummary,
    MyMembership,
    Order,
    PaymentLine,
    NextTier,
    PoolDetail,
    PoolSummary,
    ProductDemand,
    ProductCard,
    ProductDetailCard,
    RecentWish,
    RetailerPoolDetail,
    RetailerPoolMember,
    RetailerProduct,
    TierOut,
    UserOut,
)
from app.services import clock, pool_engine


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        role=user.role,
        retailer_id=user.retailer_id,
        card_label=user.card_label,
        is_simulated=user.is_simulated,
    )


def _card_fields(session: Session, product: Product) -> dict:
    retailer = session.get(Retailer, product.retailer_id)
    return dict(
        id=product.id,
        name=product.name,
        image_url=product.image_url,
        category=product.category,
        style_tags=product.style_tags,
        retailer_name=retailer.name if retailer else "",
        list_price_cents=product.list_price_cents,
    )


def product_card(session: Session, product: Product) -> ProductCard:
    return ProductCard(**_card_fields(session, product))


def _summary_fields(session: Session, pool: Pool) -> dict:
    product = session.get(Product, pool.product_id)
    tiers = pool_engine.get_tiers(session, pool)
    count = pool_engine.active_count(session, pool)
    nxt = pool_engine.next_tier(tiers, count)
    now = clock.now(session)
    return dict(
        id=pool.id,
        status=pool.status,
        participants=count,
        tiers=[
            TierOut(
                ordinal=t.ordinal,
                min_participants=t.min_participants,
                discount_cents=t.discount_cents,
                price_cents=pool_engine.tier_price(product, t),
                reached=t.min_participants <= count,
            )
            for t in tiers
        ],
        current_price_cents=pool_engine.current_price(product, tiers, count),
        next_tier=NextTier(
            ordinal=nxt.ordinal,
            needed=nxt.min_participants - count,
            price_cents=pool_engine.tier_price(product, nxt),
        )
        if nxt
        else None,
        deadline=clock.iso(pool.deadline),
        time_left_seconds=max(0, int((pool.deadline - now).total_seconds())),
        stock_cap=pool.stock_cap,
    )


def pool_summary(session: Session, pool: Pool) -> PoolSummary:
    product = session.get(Product, pool.product_id)
    return PoolSummary(product=product_card(session, product), **_summary_fields(session, pool))


def pool_detail(session: Session, pool: Pool, viewer: User | None) -> PoolDetail:
    product = session.get(Product, pool.product_id)
    membership = None
    if viewer is not None:
        member = session.exec(
            select(PoolMember).where(PoolMember.pool_id == pool.id, PoolMember.user_id == viewer.id)
        ).first()
        if member:
            membership = MyMembership(
                status=member.status, charged_cents=member.charged_cents, refunded_cents=member.refunded_cents
            )
    return PoolDetail(
        product=ProductDetailCard(
            **_card_fields(session, product), description=product.description, dimensions=product.dimensions
        ),
        my_membership=membership,
        final_price_cents=pool.final_price_cents,
        **_summary_fields(session, pool),
    )


def order(session: Session, member: PoolMember) -> Order:
    pool = session.get(Pool, member.pool_id)
    product = session.get(Product, pool.product_id)
    pays = session.exec(
        select(Payment).where(Payment.pool_member_id == member.id).order_by(Payment.created_at, Payment.id)
    ).all()
    return Order(
        pool_id=pool.id,
        product=product_card(session, product),
        pool_status=pool.status,
        member_status=member.status,
        charged_cents=member.charged_cents,
        refunded_cents=member.refunded_cents,
        net_paid_cents=member.charged_cents - member.refunded_cents,
        payments=[
            PaymentLine(kind=p.kind, amount_cents=p.amount_cents, status=p.status, created_at=clock.iso(p.created_at))
            for p in pays
        ],
    )


def demand_summary(session: Session, product: Product) -> DemandSummary:
    hits = session.exec(select(DemandHit).where(DemandHit.product_id == product.id)).all()
    week_ago = clock.now(session) - timedelta(days=7)
    total = len(hits)
    return DemandSummary(
        total_hits=total,
        last_7_days=sum(1 for h in hits if h.created_at >= week_ago),
        threshold=product.demand_threshold,
        threshold_reached=product.demand_threshold is not None and total >= product.demand_threshold,
    )


RECENT_WISHES = 10


def product_demand(session: Session, product: Product) -> ProductDemand:
    """Demand stats plus the Wishes behind the most recent Demand Hits, newest first."""
    summary = demand_summary(session, product)
    wishes = session.exec(
        select(Wish)
        .join(DemandHit, DemandHit.wish_id == Wish.id)
        .where(DemandHit.product_id == product.id)
        .order_by(DemandHit.created_at.desc(), DemandHit.id.desc())
        .limit(RECENT_WISHES)
    ).all()
    return ProductDemand(
        total_hits=summary.total_hits,
        last_7_days=summary.last_7_days,
        threshold=summary.threshold,
        recent_wishes=[RecentWish(text=w.text, created_at=clock.iso(w.created_at)) for w in wishes],
    )


def latest_pool(session: Session, product: Product) -> Pool | None:
    return session.exec(select(Pool).where(Pool.product_id == product.id).order_by(Pool.id.desc())).first()


def retailer_pool_detail(session: Session, pool: Pool) -> RetailerPoolDetail:
    """PoolDetail plus every Member (including those who left) and net revenue (charges minus refunds)."""
    rows = session.exec(
        select(PoolMember, User)
        .join(User, User.id == PoolMember.user_id)
        .where(PoolMember.pool_id == pool.id)
        .order_by(PoolMember.joined_at, PoolMember.id)
    ).all()
    detail = pool_detail(session, pool, None)
    return RetailerPoolDetail(
        **detail.model_dump(),
        members=[
            RetailerPoolMember(name=u.name, status=m.status, charged_cents=m.charged_cents,
                               refunded_cents=m.refunded_cents, joined_at=clock.iso(m.joined_at))
            for m, u in rows
        ],
        revenue_cents=sum(m.charged_cents - m.refunded_cents for m, _ in rows),
    )


def retailer_product(session: Session, product: Product) -> RetailerProduct:
    hidden = product.visibility == "hidden"
    pool = None if hidden else latest_pool(session, product)
    return RetailerProduct(
        **_card_fields(session, product),
        visibility=product.visibility,
        floor_price_cents=product.floor_price_cents,
        demand=demand_summary(session, product) if hidden else None,
        pool=pool_summary(session, pool) if pool else None,
    )
