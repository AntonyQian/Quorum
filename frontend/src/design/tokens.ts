import type { MemberStatus, PoolStatus, UserRole } from "@/lib/types";

/**
 * Quorum visual recipes.
 * The written system is `system.md` in this folder. Screens use these names
 * instead of one-off colors, type sizes, or status copy.
 */

export const POLL_INTERVAL_MS = 3000;

export const layout = {
  page: "mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5 px-3 py-4",
  topBar: "sticky top-0 z-40 border-b bg-background/90 backdrop-blur-md",
  topBarInner: "mx-auto flex h-11 w-full max-w-6xl items-center gap-2 px-3",
  grid: "grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3",
  cluster: "flex flex-wrap items-center gap-2",
  stack: "flex flex-col gap-6",
} as const;

export const typeScale = {
  wordmark: "font-heading text-lg font-semibold tracking-tight text-foreground",
  display: "font-heading text-3xl font-semibold tracking-tight text-balance",
  title: "font-heading text-base font-medium leading-snug",
  price: "text-lg font-semibold tracking-tight text-primary tabular-nums",
  priceLead:
    "text-2xl font-semibold tracking-tight text-primary tabular-nums",
  next: "text-sm font-medium tracking-tight text-foreground tabular-nums",
  list: "text-lg font-semibold tracking-tight text-foreground tabular-nums",
  compare: "text-sm font-normal text-muted-foreground line-through tabular-nums",
  savings: "text-sm font-semibold text-primary tabular-nums",
  meta: "text-sm text-muted-foreground",
  eyebrow:
    "text-xs font-medium tracking-wide text-muted-foreground uppercase",
} as const;

export const glass = {
  pill: "w-full rounded-full border border-border/70 bg-background/75 px-5 py-2.5 backdrop-blur-md",
} as const;

export const chip = {
  base: "inline-flex h-8 items-center rounded-full px-3 text-sm font-medium transition-colors",
  selected: "bg-primary text-primary-foreground",
  idle: "bg-secondary text-secondary-foreground hover:bg-accent",
} as const;

export const bar = {
  track: "h-2 overflow-hidden rounded-full bg-muted",
  fill: "h-full rounded-full bg-primary",
  fillMuted: "h-full rounded-full bg-muted-foreground/40",
  marker:
    "size-3 rounded-full border-2 border-background bg-muted-foreground/40 ring-1 ring-border",
  markerReached:
    "size-3 rounded-full border-2 border-background bg-primary ring-1 ring-primary",
  markerLabel: "mt-2 text-xs text-muted-foreground tabular-nums",
} as const;

export const skeleton = "animate-pulse rounded-xl bg-muted";

export const poolStatus: Record<
  PoolStatus,
  { label: string; badge: string; note: string }
> = {
  open: {
    label: "Open",
    badge: "border-transparent bg-status-open text-primary-foreground",
    note: "Join is free until this Pool Locks.",
  },
  locked: {
    label: "Locked",
    badge: "border-transparent bg-status-locked text-foreground",
    note: "Locked. Members are charged, and a higher Tier can still lower the price.",
  },
  completed: {
    label: "Completed",
    badge: "border-transparent bg-status-completed text-primary-foreground",
    note: "Completed. Every Member paid the final Tier price.",
  },
  failed: {
    label: "Failed",
    badge: "border-transparent bg-status-failed text-primary-foreground",
    note: "Failed. This Pool didn't reach Tier 1, so nobody was charged.",
  },
};

/** The Demo drawer: a panel sliding in from the right over a dimmed page. */
export const demo = {
  backdrop:
    "fixed inset-0 z-50 bg-foreground/20 transition-opacity duration-200 data-[starting-style]:opacity-0 data-[ending-style]:opacity-0",
  panel:
    "fixed inset-y-0 right-0 z-50 flex w-full max-w-sm flex-col gap-5 overflow-y-auto border-l bg-background p-4 shadow-xl outline-none transition-transform duration-200 data-[starting-style]:translate-x-full data-[ending-style]:translate-x-full",
  section: "flex flex-col gap-2 border-t border-border pt-4",
  field: "flex flex-col gap-1",
  input:
    "h-8 rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
} as const;

export const memberStatusLabel: Record<MemberStatus, string> = {
  pending: "Member, not charged yet",
  charged: "Member, charged",
  left: "Left",
  payment_failed: "Card declined",
};

export const MOMENT_MS = 4000;

const momentBanner =
  "animate-in fade-in slide-in-from-top-2 duration-500 rounded-xl px-4 py-3 text-sm font-medium text-foreground ring-2";
const momentRing =
  "rounded-xl ring-2 ring-offset-4 ring-offset-background transition-shadow duration-700";

/**
 * Shown for a few seconds when polling sees a Pool Lock or complete: a banner
 * that fades in, and a ring around the price block, both in the status color.
 */
export const poolMoment: Partial<
  Record<PoolStatus, { text: string; banner: string; ring: string }>
> = {
  locked: {
    text: "This Pool just Locked. Every Member was charged at once.",
    banner: `${momentBanner} bg-status-locked/15 ring-status-locked`,
    ring: `${momentRing} ring-status-locked`,
  },
  completed: {
    text: "This Pool just completed. Every Member paid the final Tier price.",
    banner: `${momentBanner} bg-status-completed/15 ring-status-completed`,
    ring: `${momentRing} ring-status-completed`,
  },
};

/** The price block's ring when no moment is playing, so the ring can fade out. */
export const momentRest = `${momentRing} ring-transparent`;

/** The Join panel and the Member line under the price. */
export const memberPanel = {
  box: "flex flex-col gap-3 rounded-xl bg-secondary p-4",
  line: "text-sm font-medium text-foreground",
  error: "text-sm text-destructive",
} as const;

/** A text link inside a page, such as "All Pools". */
export const textLink = "text-sm font-medium text-primary";

/** A payment attempt that failed, on My Orders. */
export const failedAmount = "text-muted-foreground line-through tabular-nums";

export const categories = [
  { id: "dining_table", label: "Dining" },
  { id: "sofa", label: "Sofas" },
  { id: "seating", label: "Seating" },
  { id: "chair", label: "Chairs" },
  { id: "desk", label: "Desks" },
  { id: "bookshelf", label: "Bookshelves" },
  { id: "storage", label: "Storage" },
  { id: "lighting", label: "Lighting" },
  { id: "bedroom", label: "Bedroom" },
] as const;

export function categoryLabel(id: string): string {
  const known = categories.find((category) => category.id === id)?.label;
  if (known) return known;
  const words = id.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export const poolScopes = {
  live: { label: "Live", statuses: ["open", "locked"] as const },
  settled: { label: "Settled", statuses: ["completed", "failed"] as const },
};

export function roleLabel(role: UserRole): string {
  return role === "retailer" ? "Retailer" : "Shopper";
}

export function memberCountLabel(count: number): string {
  return `${count} ${count === 1 ? "Member" : "Members"}`;
}
