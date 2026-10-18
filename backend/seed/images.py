"""Unsplash image URLs matched to furniture categories (SPEC seed)."""

from __future__ import annotations


def unsplash(photo_id: str) -> str:
    return f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w=1200&q=80"


# Category defaults — each product may override with a more specific photo.
BY_CATEGORY: dict[str, str] = {
    "bookshelf": unsplash("photo-1594620302200-9a762244a156"),
    "sofa": unsplash("photo-1555041469-a586c61ea9bc"),
    "chair": unsplash("photo-1506439773649-6e0eb8676020"),
    "dining_table": unsplash("photo-1615066390971-03e4e1c36ddf"),
    "desk": unsplash("photo-1518455027359-f3f8164ba6bd"),
    "storage": unsplash("photo-1595428774223-5482c1424c0b"),
    "lighting": unsplash("photo-1513506853909-43486f947661"),
    "bedroom": unsplash("photo-1631049307264-da0ec9d70308"),
    "seating": unsplash("photo-1540574160426-d7f191a314ae"),
}

# Named overrides when the category alone is too broad.
BY_PRODUCT: dict[str, str] = {
    "Ash Coffee Table": unsplash("photo-1532372528847-419a39add0d7"),
    "Walnut Side Table": unsplash("photo-1532372528847-419a39add0d7"),
    "Vintage Floor Lamp": unsplash("photo-1507473889263-9902eaa6224e"),
    "Felt Pendant Light": unsplash("photo-1524482765428-f9b0390a5aec"),
    "Oak Media Console": unsplash("photo-1586023492125-27b2c045efd7"),
    "Retro Sideboard": unsplash("photo-1586023492125-27b2c045efd7"),
    "Cedar Chest": unsplash("photo-1595514536987-1328c85a0591"),
    "Oak Wardrobe": unsplash("photo-1616594039964-ae9021a400a0"),
    "Rattan Armchair": unsplash("photo-1601044871170-0f9b1a4e3781"),
    "Grey Corner Sofa": unsplash("photo-1493663284031-b7e3aefcae8e"),
    "Leather Chesterfield": unsplash("photo-1551298370-9d7d4611483f"),
}


def image_for(name: str, category: str) -> str:
    return BY_PRODUCT.get(name) or BY_CATEGORY.get(category, BY_CATEGORY["storage"])
