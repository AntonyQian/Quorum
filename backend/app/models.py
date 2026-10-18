"""SQLModel tables (SPEC §7). Datetimes are naive UTC; the API serialises them as ISO-8601 with a Z."""

from pydantic import NaiveDatetime

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


class Retailer(SQLModel, table=True):
    __tablename__ = "retailers"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    tagline: str = ""
    logo_url: str = ""


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    role: str  # 'shopper' | 'retailer' | 'admin'
    retailer_id: int | None = Field(default=None, foreign_key="retailers.id")
    is_simulated: bool = False
    card_label: str | None = None
    stripe_customer_id: str | None = None
    stripe_payment_method_id: str | None = None
    card_declines: bool = False


class Product(SQLModel, table=True):
    __tablename__ = "products"
    id: int | None = Field(default=None, primary_key=True)
    retailer_id: int = Field(foreign_key="retailers.id")
    name: str
    description: str = ""
    category: str
    style_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    dimensions: str = ""
    image_url: str = ""
    list_price_cents: int
    floor_price_cents: int
    visibility: str = "hidden"  # 'hidden' | 'public'
    demand_threshold: int | None = None
    created_at: NaiveDatetime


class Pool(SQLModel, table=True):
    __tablename__ = "pools"
    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id")
    status: str = "open"  # 'open' | 'locked' | 'completed' | 'failed'
    opened_at: NaiveDatetime
    deadline: NaiveDatetime
    stock_cap: int | None = None
    locked_at: NaiveDatetime | None = None
    closed_at: NaiveDatetime | None = None
    final_price_cents: int | None = None


class Tier(SQLModel, table=True):
    __tablename__ = "tiers"
    id: int | None = Field(default=None, primary_key=True)
    pool_id: int = Field(foreign_key="pools.id")
    ordinal: int  # 1-3
    min_participants: int
    discount_cents: int


class PoolMember(SQLModel, table=True):
    __tablename__ = "pool_members"
    id: int | None = Field(default=None, primary_key=True)
    pool_id: int = Field(foreign_key="pools.id")
    user_id: int = Field(foreign_key="users.id")
    status: str = "pending"  # 'pending' | 'charged' | 'left' | 'payment_failed'
    joined_at: NaiveDatetime
    charged_cents: int = 0
    refunded_cents: int = 0


class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    id: int | None = Field(default=None, primary_key=True)
    pool_member_id: int = Field(foreign_key="pool_members.id")
    kind: str  # 'charge' | 'refund'
    amount_cents: int
    status: str  # 'succeeded' | 'failed'
    provider_ref: str = ""
    created_at: NaiveDatetime


class Wish(SQLModel, table=True):
    __tablename__ = "wishes"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    text: str
    parsed: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: NaiveDatetime


class DemandHit(SQLModel, table=True):
    __tablename__ = "demand_hits"
    __table_args__ = (UniqueConstraint("product_id", "user_id"),)
    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id")
    user_id: int = Field(foreign_key="users.id")
    wish_id: int = Field(foreign_key="wishes.id")
    created_at: NaiveDatetime


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    kind: str
    title: str
    body: str = ""
    link: str | None = None
    read: bool = False
    created_at: NaiveDatetime


class SimClock(SQLModel, table=True):
    __tablename__ = "sim_clock"
    id: int = Field(default=1, primary_key=True)
    now: NaiveDatetime
