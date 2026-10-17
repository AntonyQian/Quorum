"""Load seed.json into a fresh database: python -m seed.seed

This is the starter seed. SPEC §10 asks for ~25 products and richer pool states (a completed pool with
refunds, more hidden listings); extend seed.json as the demo needs them.
"""

import json
from datetime import timedelta
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, select

from app.db import drop_db, engine, init_db
from app.models import DemandHit, Pool, PoolMember, Product, Retailer, Tier, User, Wish
from app.services import clock, payments, pool_engine

SEED_FILE = Path(__file__).with_name("seed.json")
CARD = payments.WORKING_CARD_LABEL


def seed(session: Session) -> None:
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    now = clock.set_now(session, clock.DEFAULT_START)

    retailers: dict[str, Retailer] = {}
    for r in data["retailers"]:
        retailer = Retailer(**r)
        session.add(retailer)
        session.commit()
        retailers[r["name"]] = retailer
        session.add(User(name=f"{r['name']} Admin", role="retailer", retailer_id=retailer.id))

    for s in data["shoppers"]:
        session.add(User(name=s["name"], role="shopper"))  # no saved card: demo the card flow

    sims: list[User] = []
    for i in range(1, data["simulated_shopper_count"] + 1):
        sim = User(name=f"Sim Shopper {i}", role="shopper", is_simulated=True, card_label=CARD)
        session.add(sim)
        sims.append(sim)
    sims[0].name = data["declining_shopper_name"]
    sims[0].card_declines = True
    session.commit()

    for p in data["products"]:
        pool_spec, hidden_spec = p.get("pool"), p.get("hidden")
        fields = {k: v for k, v in p.items() if k not in ("retailer", "pool", "hidden")}
        product = Product(
            retailer_id=retailers[p["retailer"]].id,
            visibility="public" if pool_spec else "hidden",
            demand_threshold=hidden_spec["demand_threshold"] if hidden_spec else None,
            created_at=now,
            **fields,
        )
        session.add(product)
        session.commit()

        if pool_spec:
            pool = Pool(product_id=product.id, opened_at=now, deadline=now + timedelta(days=pool_spec["deadline_days"]))
            session.add(pool)
            session.commit()
            for ordinal, (minimum, discount) in enumerate(pool_spec["tiers"], start=1):
                session.add(Tier(pool_id=pool.id, ordinal=ordinal, min_participants=minimum, discount_cents=discount))
            # Skip the declining shopper so seeded pools fill predictably.
            for sim in sims[1 : 1 + pool_spec["fill"]]:
                session.add(PoolMember(pool_id=pool.id, user_id=sim.id, joined_at=now))
            session.commit()
            pool_engine.evaluate_pool(session, pool, now)

        if hidden_spec:
            for sim in sims[: hidden_spec["hits"]]:
                wish = Wish(user_id=sim.id, text=f"Looking for a {product.name.lower()}", parsed={}, created_at=now)
                session.add(wish)
                session.commit()
                session.add(DemandHit(product_id=product.id, user_id=sim.id, wish_id=wish.id, created_at=now))
            session.commit()


def reset_and_seed(bind: Engine = engine) -> None:
    """Drop, recreate, and reload every table, so re-running always yields the same starter data."""
    drop_db(bind)
    init_db(bind)
    with Session(bind) as session:
        seed(session)


if __name__ == "__main__":
    reset_and_seed()
    with Session(engine) as session:
        print(f"Seeded {len(session.exec(select(Product)).all())} products, {len(session.exec(select(User)).all())} users.")
