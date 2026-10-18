"""Retailer Products and opening Pools on them (SPEC §4 Validation, §8 Retailer)."""

from datetime import timedelta

from sqlmodel import Session, select

from app.errors import api_error, not_found
from app.models import Pool, Product, Tier, User
from app.schemas import PoolCreate, ProductCreate, ProductUpdate
from app.services import clock

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
        raise invalid_tiers("Tier 1 needs at least 1 participant and a positive discount")
    for (prev_min, prev_disc), (cur_min, cur_disc) in zip(tiers, tiers[1:]):
        if cur_min <= prev_min or cur_disc <= prev_disc:
            raise invalid_tiers("Tier participants and discounts must strictly increase")
    for i, (_, disc) in enumerate(tiers, start=1):
        if list_price_cents - disc < floor_price_cents:
            raise invalid_tiers(f"Tier {i} price is below the Floor Price")


def validate_pool(pool: PoolCreate, list_price_cents: int, floor_price_cents: int) -> None:
    if not 1 <= pool.deadline_days <= MAX_DEADLINE_DAYS:
        raise invalid_tiers(f"Deadline must be between 1 and {MAX_DEADLINE_DAYS} days")
    if pool.stock_cap is not None and pool.stock_cap < 1:
        raise invalid_tiers("Stock cap must be at least 1")
    check_tiers([(t.min_participants, t.discount_cents) for t in pool.tiers], list_price_cents, floor_price_cents)


def _check_prices(list_price_cents: int, floor_price_cents: int) -> None:
    if floor_price_cents < 0 or list_price_cents <= 0:
        raise invalid_request("Prices must be positive")
    if floor_price_cents > list_price_cents:
        raise invalid_request("Floor Price cannot exceed the list price")


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
        open_pool(session, product, body.pool)
    session.commit()
    session.refresh(product)
    return product


def get_own_product(session: Session, retailer: User, product_id: int) -> Product:
    """The retailer's own Product, or 404 `not_found` (another retailer's Product is not visible)."""
    product = session.get(Product, product_id)
    if product is None or product.retailer_id != retailer.retailer_id:
        raise not_found("Product")
    return product


def update_product(session: Session, product: Product, body: ProductUpdate) -> Product:
    changes = body.model_dump(exclude_unset=True)
    for required in ("name", "category", "list_price_cents", "floor_price_cents", "visibility"):
        if required in changes and changes[required] is None:
            raise invalid_request(f"{required} cannot be null")
    list_price = changes.get("list_price_cents", product.list_price_cents)
    floor_price = changes.get("floor_price_cents", product.floor_price_cents)
    _check_prices(list_price, floor_price)

    pool = session.exec(select(Pool).where(Pool.product_id == product.id).order_by(Pool.id.desc())).first()
    visibility = changes.get("visibility", product.visibility)
    if visibility != product.visibility:
        if visibility == "public":
            raise invalid_request("Launch a Pool to make a Hidden Listing public")
        if pool is not None and pool.status in ("open", "locked"):
            raise invalid_request("Cannot hide a Product while its Pool is running")
    if pool is not None and pool.status in ("open", "locked") and (
        list_price != product.list_price_cents or floor_price != product.floor_price_cents
    ):
        if pool.status == "locked" and list_price != product.list_price_cents:
            raise invalid_request("Cannot change the list price after the Pool has Locked")
        tiers = session.exec(select(Tier).where(Tier.pool_id == pool.id).order_by(Tier.ordinal)).all()
        check_tiers([(t.min_participants, t.discount_cents) for t in tiers], list_price, floor_price)

    for key, value in changes.items():
        setattr(product, key, value)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product
