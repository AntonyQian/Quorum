"""Response shapes (SPEC §8)."""

from typing import Literal

from pydantic import BaseModel

PoolStatus = Literal["open", "locked", "completed", "failed"]
MemberStatus = Literal["pending", "charged", "left", "payment_failed"]


class UserOut(BaseModel):
    id: int
    name: str
    role: str
    retailer_id: int | None
    card_label: str | None
    is_simulated: bool


class TierOut(BaseModel):
    ordinal: int
    min_participants: int
    discount_cents: int
    price_cents: int
    reached: bool


class ProductCard(BaseModel):
    id: int
    name: str
    image_url: str
    category: str
    style_tags: list[str]
    retailer_name: str
    list_price_cents: int


class ProductDetailCard(ProductCard):
    description: str
    dimensions: str


class NextTier(BaseModel):
    ordinal: int
    needed: int
    price_cents: int


class PoolSummary(BaseModel):
    id: int
    product: ProductCard
    status: PoolStatus
    participants: int
    tiers: list[TierOut]
    current_price_cents: int
    next_tier: NextTier | None
    deadline: str
    time_left_seconds: int
    stock_cap: int | None


class MyMembership(BaseModel):
    status: MemberStatus
    charged_cents: int
    refunded_cents: int


class PoolDetail(PoolSummary):
    product: ProductDetailCard
    my_membership: MyMembership | None
    final_price_cents: int | None
