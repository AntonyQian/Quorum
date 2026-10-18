export type UserRole = "shopper" | "retailer";
export type PoolStatus = "open" | "locked" | "completed" | "failed";
export type MemberStatus = "pending" | "charged" | "left" | "payment_failed";
export type Visibility = "hidden" | "public";

export type User = {
  id: number;
  name: string;
  role: UserRole;
  retailer_id: number | null;
  card_label: string | null;
  is_simulated: boolean;
};

export type Tier = {
  ordinal: number;
  min_participants: number;
  discount_cents: number;
  price_cents: number;
  reached: boolean;
};

export type ProductCard = {
  id: number;
  name: string;
  image_url: string;
  category: string;
  style_tags: string[];
  retailer_name: string;
  list_price_cents: number;
};

export type NextTier = {
  ordinal: number;
  needed: number;
  price_cents: number;
};

export type PoolSummary = {
  id: number;
  product: ProductCard;
  status: PoolStatus;
  participants: number;
  tiers: Tier[];
  current_price_cents: number;
  next_tier: NextTier | null;
  deadline: string;
  time_left_seconds: number;
  stock_cap: number | null;
};

export type Membership = {
  status: MemberStatus;
  charged_cents: number;
  refunded_cents: number;
};

export type PoolDetail = PoolSummary & {
  product: ProductCard & { description: string; dimensions: string };
  my_membership: Membership | null;
  final_price_cents: number | null;
};

export type Notification = {
  id: number;
  kind: string;
  title: string;
  body: string;
  link: string | null;
  read: boolean;
  created_at: string;
};

export type NotificationList = {
  unread: number;
  items: Notification[];
};

export type Order = {
  pool_id: number;
  product: ProductCard;
  pool_status: PoolStatus;
  member_status: MemberStatus;
  charged_cents: number;
  refunded_cents: number;
  net_paid_cents: number;
  payments: {
    kind: "charge" | "refund";
    amount_cents: number;
    status: "succeeded" | "failed";
    created_at: string;
  }[];
};

export type RecommendResponse = {
  wish_id: number;
  parsed: {
    category: string | null;
    budget_max_cents: number | null;
    style_tags: string[];
    size_notes: string | null;
  };
  recommendations: { pool: PoolSummary }[];
  suggestions: { pool: PoolSummary }[];
};

export type PoolCreate = {
  deadline_days: number;
  stock_cap?: number | null;
  tiers: { min_participants: number; discount_cents: number }[];
};

export type ProductCreate = {
  name: string;
  description: string;
  category: string;
  style_tags: string[];
  dimensions: string;
  image_url: string;
  list_price_cents: number;
  floor_price_cents: number;
  visibility: Visibility;
  demand_threshold?: number | null;
  pool?: PoolCreate;
};

export type RetailerProduct = ProductCard & {
  visibility: Visibility;
  floor_price_cents: number;
  demand: {
    total_hits: number;
    last_7_days: number;
    threshold: number | null;
    threshold_reached: boolean;
  } | null;
  pool: PoolSummary | null;
};

export type Demand = {
  total_hits: number;
  last_7_days: number;
  threshold: number | null;
  recent_wishes: { text: string; created_at: string }[];
};

export type RetailerPool = PoolDetail & {
  members: {
    name: string;
    status: MemberStatus;
    charged_cents: number;
    refunded_cents: number;
    joined_at: string;
  }[];
  revenue_cents: number;
};

export type ApiErrorBody = {
  detail: { code: string; message: string };
};
