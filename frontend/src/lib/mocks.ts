import type {
  Demand,
  NotificationList,
  Order,
  PoolDetail,
  PoolSummary,
  ProductCard,
  RecommendResponse,
  RetailerPool,
  RetailerProduct,
  User,
} from "./types";

function photo(path: string): string {
  return `https://images.unsplash.com/${path}?auto=format&fit=crop&w=1200&q=80`;
}

export const users: User[] = [
  {
    id: 1,
    name: "Alice",
    role: "shopper",
    retailer_id: null,
    card_label: null,
    is_simulated: false,
  },
  {
    id: 2,
    name: "Bob",
    role: "shopper",
    retailer_id: null,
    card_label: null,
    is_simulated: false,
  },
  {
    id: 3,
    name: "Oak & Co.",
    role: "retailer",
    retailer_id: 1,
    card_label: null,
    is_simulated: false,
  },
  {
    id: 4,
    name: "Nordlund",
    role: "retailer",
    retailer_id: 2,
    card_label: null,
    is_simulated: false,
  },
  {
    id: 5,
    name: "ReLoft",
    role: "retailer",
    retailer_id: 3,
    card_label: null,
    is_simulated: false,
  },
  {
    id: 6,
    name: "Sam",
    role: "shopper",
    retailer_id: null,
    card_label: "Visa •••• 4242",
    is_simulated: true,
  },
];

const maple: ProductCard = {
  id: 11,
  name: "Maple Dining Table",
  image_url: photo("photo-1604578762246-41134e37f9cc"),
  category: "dining_table",
  style_tags: ["maple", "solid-wood"],
  retailer_name: "Oak & Co.",
  list_price_cents: 80000,
};

const sofa: ProductCard = {
  id: 12,
  name: "Cloud Sofa",
  image_url: photo("photo-1555041469-a586c61ea9bc"),
  category: "sofa",
  style_tags: ["linen", "scandinavian"],
  retailer_name: "Nordlund",
  list_price_cents: 220000,
};

const chair: ProductCard = {
  id: 13,
  name: "Oak Chair",
  image_url: photo("photo-1506439773649-6e0eb8cfb237"),
  category: "seating",
  style_tags: ["oak", "refurbished"],
  retailer_name: "ReLoft",
  list_price_cents: 45000,
};

const dresser: ProductCard = {
  id: 14,
  name: "Oak Dresser",
  image_url: photo("photo-1595428774223-ef52624120d2"),
  category: "storage",
  style_tags: ["oak", "solid-wood"],
  retailer_name: "Oak & Co.",
  list_price_cents: 96000,
};

const lamp: ProductCard = {
  id: 15,
  name: "Arc Lamp",
  image_url: photo("photo-1507473885765-e6ed057f782c"),
  category: "lighting",
  style_tags: ["brass", "scandinavian"],
  retailer_name: "Nordlund",
  list_price_cents: 18000,
};

const bed: ProductCard = {
  id: 16,
  name: "Linen Bed",
  image_url: photo("photo-1505693416388-ac5ce068fe85"),
  category: "bedroom",
  style_tags: ["linen", "oak"],
  retailer_name: "ReLoft",
  list_price_cents: 140000,
};

export const poolSummaries: PoolSummary[] = [
  {
    id: 1,
    product: maple,
    status: "open",
    participants: 8,
    tiers: [
      {
        ordinal: 1,
        min_participants: 10,
        discount_cents: 16000,
        price_cents: 64000,
        reached: false,
      },
      {
        ordinal: 2,
        min_participants: 25,
        discount_cents: 25000,
        price_cents: 55000,
        reached: false,
      },
    ],
    current_price_cents: 64000,
    next_tier: { ordinal: 1, needed: 2, price_cents: 64000 },
    deadline: "2026-10-19T21:00:00Z",
    time_left_seconds: 172800,
    stock_cap: null,
  },
  {
    id: 2,
    product: sofa,
    status: "open",
    participants: 4,
    tiers: [
      {
        ordinal: 1,
        min_participants: 15,
        discount_cents: 40000,
        price_cents: 180000,
        reached: false,
      },
      {
        ordinal: 2,
        min_participants: 30,
        discount_cents: 60000,
        price_cents: 160000,
        reached: false,
      },
    ],
    current_price_cents: 180000,
    next_tier: { ordinal: 1, needed: 11, price_cents: 180000 },
    deadline: "2026-10-17T22:00:00Z",
    time_left_seconds: 3600,
    stock_cap: null,
  },
  {
    id: 3,
    product: chair,
    status: "locked",
    participants: 12,
    tiers: [
      {
        ordinal: 1,
        min_participants: 10,
        discount_cents: 8000,
        price_cents: 37000,
        reached: true,
      },
      {
        ordinal: 2,
        min_participants: 20,
        discount_cents: 14000,
        price_cents: 31000,
        reached: false,
      },
    ],
    current_price_cents: 37000,
    next_tier: { ordinal: 2, needed: 8, price_cents: 31000 },
    deadline: "2026-10-18T21:00:00Z",
    time_left_seconds: 86400,
    stock_cap: 30,
  },
  {
    id: 4,
    product: dresser,
    status: "completed",
    participants: 18,
    tiers: [
      {
        ordinal: 1,
        min_participants: 8,
        discount_cents: 12000,
        price_cents: 84000,
        reached: true,
      },
      {
        ordinal: 2,
        min_participants: 16,
        discount_cents: 22000,
        price_cents: 74000,
        reached: true,
      },
    ],
    current_price_cents: 74000,
    next_tier: null,
    deadline: "2026-10-10T21:00:00Z",
    time_left_seconds: 0,
    stock_cap: null,
  },
  {
    id: 5,
    product: lamp,
    status: "failed",
    participants: 3,
    tiers: [
      {
        ordinal: 1,
        min_participants: 10,
        discount_cents: 3000,
        price_cents: 15000,
        reached: false,
      },
    ],
    current_price_cents: 15000,
    next_tier: { ordinal: 1, needed: 7, price_cents: 15000 },
    deadline: "2026-10-12T21:00:00Z",
    time_left_seconds: 0,
    stock_cap: null,
  },
  {
    id: 6,
    product: bed,
    status: "open",
    participants: 10,
    tiers: [
      {
        ordinal: 1,
        min_participants: 12,
        discount_cents: 20000,
        price_cents: 120000,
        reached: false,
      },
    ],
    current_price_cents: 120000,
    next_tier: { ordinal: 1, needed: 2, price_cents: 120000 },
    deadline: "2026-10-23T21:00:00Z",
    time_left_seconds: 500000,
    stock_cap: null,
  },
];

const details: Record<
  number,
  Pick<PoolDetail, "product" | "my_membership" | "final_price_cents">
> = {
  1: {
    product: {
      ...maple,
      description: "Solid maple top with a tapered leg, built for a small dining room.",
      dimensions: "60 in wide, seats 4",
    },
    my_membership: null,
    final_price_cents: null,
  },
  2: {
    product: {
      ...sofa,
      description: "A deep linen sofa with a light oak frame.",
      dimensions: "88 in wide, seats 3",
    },
    my_membership: null,
    final_price_cents: null,
  },
  3: {
    product: {
      ...chair,
      description: "Refurbished oak side chair with a new woven seat.",
      dimensions: "18 in wide",
    },
    my_membership: {
      status: "charged",
      charged_cents: 37000,
      refunded_cents: 0,
    },
    final_price_cents: null,
  },
  4: {
    product: {
      ...dresser,
      description: "Six-drawer oak dresser, finished with oil.",
      dimensions: "54 in wide, 34 in tall",
    },
    my_membership: {
      status: "charged",
      charged_cents: 84000,
      refunded_cents: 10000,
    },
    final_price_cents: 74000,
  },
  5: {
    product: {
      ...lamp,
      description: "Brass arc lamp with a linen shade.",
      dimensions: "70 in tall",
    },
    my_membership: null,
    final_price_cents: null,
  },
  6: {
    product: {
      ...bed,
      description: "Linen-upholstered bed with an oak rail.",
      dimensions: "Queen",
    },
    my_membership: null,
    final_price_cents: null,
  },
};

export function poolDetail(id: number): PoolDetail | undefined {
  const summary = poolSummaries.find((pool) => pool.id === id);
  const extra = details[id];
  if (!summary || !extra) return undefined;
  return { ...summary, ...extra };
}

export const orders: Order[] = [
  {
    pool_id: 4,
    product: dresser,
    pool_status: "completed",
    member_status: "charged",
    charged_cents: 84000,
    refunded_cents: 10000,
    net_paid_cents: 74000,
    payments: [
      {
        kind: "charge",
        amount_cents: 84000,
        status: "succeeded",
        created_at: "2026-10-01T21:00:00Z",
      },
      {
        kind: "refund",
        amount_cents: 10000,
        status: "succeeded",
        created_at: "2026-10-10T21:00:00Z",
      },
    ],
  },
];

export const notifications: NotificationList = {
  unread: 1,
  items: [
    {
      id: 1,
      kind: "pool_locked",
      title: "Pool locked",
      body: "Oak Chair reached Tier 1.",
      link: "/pools/3",
      read: false,
      created_at: "2026-10-16T21:00:00Z",
    },
    {
      id: 2,
      kind: "tier_refund",
      title: "Tier Refund",
      body: "You were refunded $100.00 on Oak Dresser.",
      link: "/orders",
      read: true,
      created_at: "2026-10-10T21:00:00Z",
    },
  ],
};

export const recommendation: RecommendResponse = {
  wish_id: 1,
  parsed: {
    category: "dining_table",
    budget_max_cents: 80000,
    style_tags: ["maple"],
    size_notes: "seats 4",
  },
  recommendations: [{ pool: poolSummaries[0]! }],
  suggestions: [],
};

const walnut: RetailerProduct = {
  id: 31,
  name: "Walnut Dining Table",
  image_url: photo("photo-1615066390971-03e4e1c36ddf"),
  category: "dining_table",
  style_tags: ["walnut", "mid-century"],
  retailer_name: "Oak & Co.",
  list_price_cents: 90000,
  visibility: "hidden",
  floor_price_cents: 60000,
  demand: {
    total_hits: 9,
    last_7_days: 4,
    threshold: 10,
    threshold_reached: false,
  },
  pool: null,
};

export const retailerProducts: RetailerProduct[] = [
  {
    ...maple,
    visibility: "public",
    floor_price_cents: 52000,
    demand: null,
    pool: poolSummaries[0]!,
  },
  walnut,
];

export const walnutDemand: Demand = {
  total_hits: 9,
  last_7_days: 4,
  threshold: 10,
  recent_wishes: [
    {
      text: "walnut dining table for 4",
      created_at: "2026-10-17T18:00:00Z",
    },
  ],
};

export function retailerPool(id: number): RetailerPool | undefined {
  const detail = poolDetail(id);
  if (!detail) return undefined;
  return {
    ...detail,
    members: [
      {
        name: "Alice",
        status: "charged",
        charged_cents: 37000,
        refunded_cents: 0,
        joined_at: "2026-10-16T18:00:00Z",
      },
    ],
    revenue_cents: 444000,
  };
}

export const simClock = { now: "2026-10-17T21:00:00Z" };
