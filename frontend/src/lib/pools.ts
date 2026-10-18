import type { PoolStatus } from "./types";

export function formatTimeLeft(seconds: number): string {
  if (seconds <= 0) return "Ended";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${seconds}s`;
}

function unitLabel(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

/** Card caption for a Deadline. Spells the units out from time_left_seconds. */
export function formatTimeLeftWords(seconds: number): string {
  if (seconds <= 0) return "Ended";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const parts: string[] = [];
  if (days > 0) parts.push(unitLabel(days, "day", "days"));
  if (hours > 0) parts.push(unitLabel(hours, "hour", "hours"));
  if (parts.length === 0 && minutes > 0) {
    parts.push(unitLabel(minutes, "minute", "minutes"));
  }
  if (parts.length === 0) parts.push(unitLabel(seconds, "second", "seconds"));
  return parts.join(" ");
}

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/** Display a Sim Clock ISO timestamp. Does not read the browser clock. */
export function formatSimClock(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso);
  if (!match) return iso;
  const [, year, month, day, hour, minute] = match;
  const hour24 = Number(hour);
  const suffix = hour24 >= 12 ? "PM" : "AM";
  const hour12 = hour24 % 12 || 12;
  return `${MONTHS[Number(month) - 1]} ${Number(day)}, ${year}, ${hour12}:${minute} ${suffix} UTC`;
}

export function membersAwayLabel(needed: number): string {
  return `${needed} more ${needed === 1 ? "Member" : "Members"}`;
}

export type DiscountOffer = {
  listCents: number;
  active: { priceCents: number; savingsCents: number } | null;
  next: { needed: number; priceCents: number } | null;
  progressPercent: number;
  label: string;
};

/** What a card should say about the discount in effect and the next one. */
export function discountOffer(pool: {
  status: PoolStatus;
  participants: number;
  current_price_cents: number;
  next_tier: { needed: number; price_cents: number } | null;
  tiers: { min_participants: number; reached: boolean }[];
  product: { list_price_cents: number };
}): DiscountOffer {
  const listCents = pool.product.list_price_cents;
  const reached = pool.tiers.some((tier) => tier.reached);
  const savingsCents = listCents - pool.current_price_cents;
  const active =
    reached && savingsCents > 0
      ? { priceCents: pool.current_price_cents, savingsCents }
      : null;
  const live = pool.status === "open" || pool.status === "locked";
  const next =
    live && pool.next_tier
      ? { needed: pool.next_tier.needed, priceCents: pool.next_tier.price_cents }
      : null;

  if (pool.status === "failed") {
    const target = pool.tiers[0]?.min_participants ?? 1;
    return {
      listCents,
      active: null,
      next: null,
      progressPercent: Math.min(100, (pool.participants / Math.max(target, 1)) * 100),
      label: "This Pool didn't reach Tier 1",
    };
  }

  if (!next) {
    return {
      listCents,
      active,
      next: null,
      progressPercent: 100,
      label: pool.status === "completed" ? "Settled" : "Top Tier reached",
    };
  }

  const target = pool.participants + next.needed;
  return {
    listCents,
    active,
    next,
    progressPercent: Math.min(100, (pool.participants / Math.max(target, 1)) * 100),
    label: membersAwayLabel(next.needed),
  };
}

export function poolProgressCaption(pool: {
  status: PoolStatus;
  next_tier: { needed: number } | null;
}): string {
  if (pool.status === "failed") return "This Pool didn't reach Tier 1";
  if (pool.status === "completed") return "Settled";
  if (!pool.next_tier) return "Top Tier reached";
  return `Next tier in ${pool.next_tier.needed} people`;
}

export function tierProgress(pool: {
  participants: number;
  stock_cap: number | null;
  tiers: { ordinal: number; min_participants: number; reached: boolean }[];
}): {
  fillPercent: number;
  markers: { ordinal: number; percent: number; reached: boolean }[];
} {
  const lastTier = pool.tiers[pool.tiers.length - 1];
  const scale = Math.max(pool.stock_cap ?? lastTier?.min_participants ?? 1, 1);
  return {
    fillPercent: (pool.participants / scale) * 100,
    markers: pool.tiers.map((tier) => ({
      ordinal: tier.ordinal,
      percent: (tier.min_participants / scale) * 100,
      reached: tier.reached,
    })),
  };
}

export function filterPoolsByCategory<T extends { product: { category: string } }>(
  pools: T[],
  category: string | null,
): T[] {
  if (!category) return pools;
  return pools.filter((pool) => pool.product.category === category);
}

export function filterPoolsByBrowseCategory<
  T extends { product: { category: string; name: string } },
>(pools: T[], value: string): T[] {
  if (value === "all") return pools;
  if (value === "dining") {
    return pools.filter(
      (pool) =>
        pool.product.category === "dining_table" && /dining/i.test(pool.product.name),
    );
  }
  if (value === "tables") {
    return pools.filter(
      (pool) =>
        pool.product.category === "dining_table" && !/dining/i.test(pool.product.name),
    );
  }
  return pools.filter((pool) => pool.product.category === value);
}
