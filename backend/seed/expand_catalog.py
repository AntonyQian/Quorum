"""Refresh seed.json: matching images, varied prices, and extra products. Run: python -m seed.expand_catalog"""

from __future__ import annotations

import json
from pathlib import Path

from seed.images import image_for

SEED_FILE = Path(__file__).with_name("seed.json")

# Typical list prices (USD) by category — floor ≈ 65–72% of list.
LIST_USD: dict[str, tuple[int, int]] = {
    "chair": (249, 649),
    "sofa": (899, 2199),
    "dining_table": (699, 1499),
    "desk": (449, 999),
    "bookshelf": (279, 899),
    "storage": (199, 899),
    "lighting": (89, 399),
    "bedroom": (599, 1499),
    "seating": (199, 749),
}


def price_pair(category: str, *, large: bool = False) -> tuple[int, int]:
    lo, hi = LIST_USD.get(category, (399, 999))
    if large:
        lo = int(lo * 1.25)
        hi = int(hi * 1.35)
    list_usd = (lo + hi) // 2
    floor_usd = int(list_usd * 0.68)
    return list_usd * 100, floor_usd * 100


def tier_template(category: str) -> dict:
    if category in ("sofa", "dining_table", "bedroom"):
        return {"deadline_days": 18, "fill": 6, "tiers": [[10, 15000], [22, 28000]]}
    if category == "lighting":
        return {"deadline_days": 14, "fill": 4, "tiers": [[6, 2500], [14, 5000]]}
    return {"deadline_days": 12, "fill": 5, "tiers": [[8, 8000], [18, 16000]]}


NEW_PRODUCTS: list[dict] = [
    {
        "retailer": "Oak & Co.",
        "name": "Extendable Walnut Table",
        "category": "dining_table",
        "description": "Walnut table with two 40 cm leaves; seats six to ten.",
        "style_tags": ["walnut", "extendable"],
        "dimensions": "180–260 x 95 x 76 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("dining_table", large=True))),
        "pool": {"deadline_days": 16, "fill": 7, "tiers": [[12, 14000], [24, 26000]]},
    },
    {
        "retailer": "Nordlund",
        "name": "Modular Sectional",
        "category": "sofa",
        "description": "Four-piece modular sectional in charcoal weave.",
        "style_tags": ["modular", "grey"],
        "dimensions": "320 x 160 x 85 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("sofa", large=True))),
        "pool": {"deadline_days": 22, "fill": 9, "tiers": [[12, 22000], [28, 42000]]},
    },
    {
        "retailer": "ReLoft",
        "name": "Restored Eames-Style Lounge",
        "category": "seating",
        "description": "Plywood lounge chair and ottoman, newly upholstered.",
        "style_tags": ["mid-century", "walnut"],
        "dimensions": "84 x 85 x 82 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("seating"))),
        "pool": {"deadline_days": 8, "fill": 3, "tiers": [[5, 7500], [12, 14000]]},
    },
    {
        "retailer": "Oak & Co.",
        "name": "Ergonomic Desk Chair",
        "category": "chair",
        "description": "Adjustable oak and mesh task chair.",
        "style_tags": ["oak", "office"],
        "dimensions": "65 x 65 x 105 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("chair"))),
        "pool": {"deadline_days": 10, "fill": 11, "tiers": [[6, 4500], [15, 9000]]},
    },
    {
        "retailer": "Nordlund",
        "name": "King Platform Bed",
        "category": "bedroom",
        "description": "Low platform bed in whitewashed oak.",
        "style_tags": ["scandinavian", "oak"],
        "dimensions": "210 x 200 x 35 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("bedroom", large=True))),
        "pool": {"deadline_days": 20, "fill": 8, "tiers": [[10, 12000], [20, 22000]]},
    },
    {
        "retailer": "ReLoft",
        "name": "Brass Arc Floor Lamp",
        "category": "lighting",
        "description": "1970s arc lamp with new dimmer and linen shade.",
        "style_tags": ["brass", "vintage"],
        "dimensions": "110 x 40 x 200 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("lighting"))),
        "pool": {"deadline_days": 15, "fill": 2, "tiers": [[5, 2800], [12, 5500]]},
    },
    {
        "retailer": "Oak & Co.",
        "name": "Entryway Storage Bench",
        "category": "storage",
        "description": "Solid oak bench with lift-top shoe storage.",
        "style_tags": ["oak", "entryway"],
        "dimensions": "120 x 40 x 48 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("storage"))),
        "pool": {"deadline_days": 11, "fill": 4, "tiers": [[6, 5000], [14, 9500]]},
    },
    {
        "retailer": "Nordlund",
        "name": "Glass Coffee Table",
        "category": "dining_table",
        "description": "Tempered glass top on ash legs.",
        "style_tags": ["glass", "minimal"],
        "dimensions": "110 x 60 x 42 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("dining_table"))),
        "pool": {"deadline_days": 9, "fill": 5, "tiers": [[7, 6000], [16, 11000]]},
    },
    {
        "retailer": "ReLoft",
        "name": "Mid-Century TV Console",
        "category": "storage",
        "description": "Teak media unit with cane sliding doors.",
        "style_tags": ["teak", "mid-century"],
        "dimensions": "180 x 45 x 50 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("storage"))),
        "pool": {"deadline_days": 13, "fill": 6, "tiers": [[8, 8500], [18, 16000]]},
    },
    {
        "retailer": "Oak & Co.",
        "name": "Farmhouse Dining Bench",
        "category": "seating",
        "description": "Reclaimed pine bench for dining tables.",
        "style_tags": ["farmhouse", "pine"],
        "dimensions": "180 x 35 x 45 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("seating"))),
        "pool": {"deadline_days": 14, "fill": 3, "tiers": [[5, 4000], [12, 8000]]},
    },
    {
        "retailer": "Nordlund",
        "name": "Ladder Bookshelf",
        "category": "bookshelf",
        "description": "Five-tier leaning bookshelf in white oak.",
        "style_tags": ["minimal", "oak"],
        "dimensions": "60 x 40 x 190 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("bookshelf"))),
        "hidden": {"demand_threshold": 8, "hits": 2},
    },
    {
        "retailer": "ReLoft",
        "name": "Velvet Tufted Sofa",
        "category": "sofa",
        "description": "Three-seat emerald velvet sofa, reupholstered.",
        "style_tags": ["velvet", "classic"],
        "dimensions": "210 x 90 x 78 cm",
        **dict(zip(("list_price_cents", "floor_price_cents"), price_pair("sofa"))),
        "hidden": {"demand_threshold": 12, "hits": 5},
    },
]


def refresh_product(product: dict) -> None:
    name = product["name"]
    category = product["category"]
    product["image_url"] = image_for(name, category)

    if product.get("hidden") and product["list_price_cents"] == 79900 and product["floor_price_cents"] == 52900:
        large = category in ("sofa", "dining_table", "bedroom")
        list_c, floor_c = price_pair(category, large=large)
        product["list_price_cents"] = list_c
        product["floor_price_cents"] = floor_c


def main() -> None:
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    existing = {p["name"] for p in data["products"]}

    for product in data["products"]:
        refresh_product(product)

    for product in NEW_PRODUCTS:
        product = dict(product)
        product["image_url"] = image_for(product["name"], product["category"])
        if product["name"] not in existing:
            data["products"].append(product)
            existing.add(product["name"])

    SEED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {SEED_FILE.name}: {len(data['products'])} products")


if __name__ == "__main__":
    main()
