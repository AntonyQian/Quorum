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
