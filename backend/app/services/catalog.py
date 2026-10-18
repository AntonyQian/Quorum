"""Retailer Products and opening Pools on them (SPEC §4 Validation, §8 Retailer)."""

from datetime import timedelta

from sqlmodel import Session, select

from app.errors import api_error, not_found
from app.models import DemandHit, Pool, PoolMember, Product, Tier, User
from app.schemas import PoolCreate, ProductCreate, ProductUpdate
from app.services import clock, demand, notifications, pool_engine, views, wish_alerts

MAX_DEADLINE_DAYS = 30


def invalid_tiers(message: str):
    return api_error(400, "invalid_tiers", message)


def invalid_request(message: str):
    return api_error(400, "invalid_request", message)


def check_tiers(tiers: list[tuple[int, int]], list_price_cents: int, floor_price_cents: int) -> None:
    """SPEC §4: 1-3 Tiers, strictly increasing min_participants and discount_cents, every Tier price at or
    above the Floor Price. `tiers` is (min_participants, discount_cents) in ordinal order."""
    if not 1 <= len(tiers) <= 3:
        raise invalid_tiers("A Pool needs 1 to 3 Tiers")
    if tiers[0][0] < 1 or tiers[0][1] < 1:
        raise invalid_tiers("Tier 1 needs at least 1 Member and a positive discount")
    for (prev_min, prev_disc), (cur_min, cur_disc) in zip(tiers, tiers[1:]):
        if cur_min <= prev_min or cur_disc <= prev_disc:
            raise invalid_tiers("Tier Member counts and discounts must strictly increase")
    for i, (_, disc) in enumerate(tiers, start=1):
        if list_price_cents - disc < floor_price_cents:
            raise invalid_tiers(f"Tier {i} price is below the Floor Price")


def validate_pool(pool: PoolCreate, list_price_cents: int, floor_price_cents: int) -> None:
    if not 1 <= pool.deadline_days <= MAX_DEADLINE_DAYS:
        raise invalid_tiers(f"Deadline must be between 1 and {MAX_DEADLINE_DAYS} days")
    if pool.stock_cap is not None and pool.stock_cap < 1:
        raise invalid_tiers("Stock Cap must be at least 1")
    check_tiers([(t.min_participants, t.discount_cents) for t in pool.tiers], list_price_cents, floor_price_cents)


def _check_prices(list_price_cents: int, floor_price_cents: int) -> None:
    if floor_price_cents < 0 or list_price_cents <= 0:
        raise invalid_request("Prices must be positive")
    if floor_price_cents > list_price_cents:
        raise invalid_request("Floor Price cannot exceed the List Price")


def _check_threshold_value(threshold: int | None) -> None:
    if threshold is not None and threshold < 1:
        raise invalid_request("Demand Threshold must be at least 1")


def open_pool(session: Session, product: Product, spec: PoolCreate) -> Pool:
    """Validate `spec` against the Product's prices and open a Pool on it (status `open`, from the Sim Clock)."""
    validate_pool(spec, product.list_price_cents, product.floor_price_cents)
    now = clock.now(session)
    pool = Pool(product_id=product.id, status="open", opened_at=now,
                deadline=now + timedelta(days=spec.deadline_days), stock_cap=spec.stock_cap)
    session.add(pool)
    session.flush()
    for ordinal, t in enumerate(spec.tiers, start=1):
        session.add(Tier(pool_id=pool.id, ordinal=ordinal, min_participants=t.min_participants,
                         discount_cents=t.discount_cents))
    return pool


def create_product(session: Session, retailer: User, body: ProductCreate) -> Product:
    _check_prices(body.list_price_cents, body.floor_price_cents)
    _check_threshold_value(body.demand_threshold)
    if body.visibility == "public" and body.pool is None:
        raise invalid_request("A public Product needs a Pool")
    if body.visibility == "hidden" and body.pool is not None:
        raise invalid_request("A Hidden Listing has no Pool; Launch one later")
    product = Product(
        retailer_id=retailer.retailer_id,
        created_at=clock.now(session),
        **body.model_dump(exclude={"pool"}),
    )
    if body.visibility == "public":
        product.demand_threshold = None
    session.add(product)
    session.flush()
    if body.pool is not None:
        pool = open_pool(session, product, body.pool)
        wish_alerts.notify_matching_wishes(session, pool, product)
    session.commit()
    session.refresh(product)
    return product


def _owned_by(product: Product | None, retailer: User) -> bool:
    return product is not None and product.retailer_id == retailer.retailer_id


def get_own_product(session: Session, retailer: User, product_id: int) -> Product:
    """The retailer's own Product, or 404 `not_found` (another retailer's Product is not visible)."""
    product = session.get(Product, product_id)
    if not _owned_by(product, retailer):
        raise not_found("Product")
    return product


def get_own_pool(session: Session, retailer: User, pool_id: int) -> Pool:
    """A Pool on one of the retailer's own Products, or 404 `not_found`."""
    pool = session.get(Pool, pool_id)
    if pool is None or not _owned_by(session.get(Product, pool.product_id), retailer):
        raise not_found("Pool")
    return pool


def list_products(session: Session, retailer: User) -> list[Product]:
    """The retailer's Products, after evaluating each one's latest Pool so its status is current."""
    products = session.exec(
        select(Product).where(Product.retailer_id == retailer.retailer_id).order_by(Product.id)
    ).all()
    for product in products:
        pool = views.latest_pool(session, product)
        if pool is not None:
            pool_engine.evaluate_pool(session, pool)
    return list(products)


def update_product(session: Session, product: Product, body: ProductUpdate) -> Product:
    changes = body.model_dump(exclude_unset=True)
    for required in ("name", "category", "list_price_cents", "floor_price_cents", "visibility"):
        if required in changes and changes[required] is None:
            raise invalid_request(f"{required} cannot be null")
    list_price = changes.get("list_price_cents", product.list_price_cents)
    floor_price = changes.get("floor_price_cents", product.floor_price_cents)
    _check_prices(list_price, floor_price)

    pool = views.latest_pool(session, product)
    running = pool is not None and pool.status in pool_engine.LIVE
    visibility = changes.get("visibility", product.visibility)
    if visibility != product.visibility:
        if visibility == "public":
            raise invalid_request("Launch a Pool to make a Hidden Listing public")
        if running:
            raise invalid_request("Cannot hide a Product while its Pool is running")
    if "demand_threshold" in changes:
        if visibility != "hidden":
            raise invalid_request("Only a Hidden Listing has a Demand Threshold")
        _check_threshold_value(changes["demand_threshold"])
    if running and (list_price != product.list_price_cents or floor_price != product.floor_price_cents):
        if pool.status == "locked" and list_price != product.list_price_cents:
            raise invalid_request("Cannot change the List Price after the Pool has Locked")
        tiers = pool_engine.get_tiers(session, pool)
        check_tiers([(t.min_participants, t.discount_cents) for t in tiers], list_price, floor_price)

    for key, value in changes.items():
        setattr(product, key, value)
    session.add(product)
    session.flush()
    demand.check_threshold(session, product)
    session.commit()
    session.refresh(product)
    return product


def launch(session: Session, product: Product, spec: PoolCreate) -> Pool:
    """Launch a Hidden Listing: make it public, open its Pool, and notify every shopper with a Demand Hit on it."""
    if product.visibility != "hidden":
        raise invalid_request("Only a Hidden Listing can be Launched")
    pool = open_pool(session, product, spec)
    product.visibility = "public"
    session.add(product)
    shopper_ids = session.exec(select(DemandHit.user_id).where(DemandHit.product_id == product.id)).all()
    for user_id in shopper_ids:
        notifications.notify(session, user_id, "pool_launched", f"The {product.name} you asked about is now a Pool",
                             "Something you wished for just launched. Join to unlock the group price.",
                             link=f"/pools/{pool.id}")
    session.flush()
    wish_alerts.notify_matching_wishes(session, pool, product)
    session.commit()
    session.refresh(pool)
    return pool


def delete_product(session: Session, product: Product) -> None:
    """Remove a Product. Refused while any of its Pools has Members, so Orders and payments stay intact."""
    pools = session.exec(select(Pool).where(Pool.product_id == product.id)).all()
    for pool in pools:
        pool_engine.evaluate_pool(session, pool)
        if session.exec(select(PoolMember.id).where(PoolMember.pool_id == pool.id)).first() is not None:
            raise api_error(409, "product_in_use", "This Product has Pool Members and can't be removed")
    for pool in pools:
        for tier in pool_engine.get_tiers(session, pool):
            session.delete(tier)
        session.delete(pool)
    for hit in session.exec(select(DemandHit).where(DemandHit.product_id == product.id)).all():
        session.delete(hit)
    session.delete(product)
    session.commit()
