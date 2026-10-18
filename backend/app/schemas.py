"""Request and response shapes (SPEC §8)."""

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


class SetupSessionBody(BaseModel):
    return_to: str | None = None


class ConfirmSetupBody(BaseModel):
    session_id: str


class PaymentLine(BaseModel):
    kind: Literal["charge", "refund"]
    amount_cents: int
    status: Literal["succeeded", "failed"]
    created_at: str


class Order(BaseModel):
    pool_id: int
    product: ProductCard
    pool_status: PoolStatus
    member_status: MemberStatus
    charged_cents: int
    refunded_cents: int
    net_paid_cents: int
    payments: list[PaymentLine]


class NotificationOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    link: str | None
    read: bool
    created_at: str


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]


class RetailerPoolMember(BaseModel):
    name: str
    status: MemberStatus
    charged_cents: int
    refunded_cents: int
    joined_at: str


class RetailerPoolDetail(PoolDetail):
    members: list[RetailerPoolMember]
    revenue_cents: int


class TierCreate(BaseModel):
    min_participants: int
    discount_cents: int


class PoolCreate(BaseModel):
    deadline_days: int  # 1-30, checked by catalog.validate_pool (invalid_tiers)
    stock_cap: int | None = None
    tiers: list[TierCreate]


class ProductUpdate(BaseModel):
    """Partial ProductCreate without `pool` (PATCH /retailer/products/{id})."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    style_tags: list[str] | None = None
    dimensions: str | None = None
    image_url: str | None = None
    list_price_cents: int | None = None
    floor_price_cents: int | None = None
    visibility: Literal["hidden", "public"] | None = None
    demand_threshold: int | None = None


class ProductCreate(BaseModel):
    name: str
    description: str
    category: str
    style_tags: list[str]
    dimensions: str
    image_url: str
    list_price_cents: int
    floor_price_cents: int
    visibility: Literal["hidden", "public"]
    demand_threshold: int | None = None
    pool: PoolCreate | None = None


class DemandSummary(BaseModel):
    total_hits: int
    last_7_days: int
    threshold: int | None
    threshold_reached: bool


class RecentWish(BaseModel):
    text: str
    created_at: str


class ProductDemand(BaseModel):
    total_hits: int
    last_7_days: int
    threshold: int | None
    recent_wishes: list[RecentWish]


class RetailerProduct(ProductCard):
    visibility: Literal["hidden", "public"]
    floor_price_cents: int
    demand: DemandSummary | None
    pool: PoolSummary | None


class RecommendBody(BaseModel):
    text: str


class ParsedWishOut(BaseModel):
    category: str | None
    budget_max_cents: int | None
    style_tags: list[str]
    size_notes: str | None


class Recommendation(BaseModel):
    pool: PoolSummary
    fit_score: int
    reason: str


class RecommendResponse(BaseModel):
    wish_id: int
    parsed: ParsedWishOut
    recommendations: list[Recommendation]
