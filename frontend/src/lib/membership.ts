import { formatCents } from "./money";
import type { Membership, PoolStatus } from "./types";

export type JoinAction =
  | { kind: "join"; label: string }
  | { kind: "leave"; label: string }
  | { kind: "none" };

export function isActiveMember(membership: Membership | null): boolean {
  return membership?.status === "pending" || membership?.status === "charged";
}

/** The button a Shopper sees on a Pool: Join, Leave, or nothing. */
export function joinAction(pool: {
  status: PoolStatus;
  my_membership: Membership | null;
  current_price_cents: number;
  next_tier: { needed: number; price_cents: number } | null;
}): JoinAction {
  const member = isActiveMember(pool.my_membership);
  if (pool.status === "open") {
    return member ? { kind: "leave", label: "Leave" } : { kind: "join", label: "Join" };
  }
  if (pool.status === "locked" && !member) {
    // The new Member counts toward the Tier before they are charged.
    const priceCents =
      pool.next_tier && pool.next_tier.needed <= 1
        ? pool.next_tier.price_cents
        : pool.current_price_cents;
    return {
      kind: "join",
      label: `Join (you'll be charged ${formatCents(priceCents)} now)`,
    };
  }
  return { kind: "none" };
}

/** One sentence about the active account's membership, with charged and refunded amounts. */
export function membershipMessage(
  status: PoolStatus,
  membership: Membership | null,
): string | null {
  if (!membership) return null;
  if (membership.status === "left") return "You left this Pool.";
  if (membership.status === "payment_failed") {
    return "Your card was declined, so you are no longer a Member. Save another card to Join again.";
  }
  // The status note already says the Pool missed Tier 1.
  if (status === "failed") return "You were not charged.";
  const charged = formatCents(membership.charged_cents);
  if (status === "completed") {
    if (membership.refunded_cents === 0) return `You paid ${charged}.`;
    const net = formatCents(membership.charged_cents - membership.refunded_cents);
    return `You were charged ${charged} and got a ${formatCents(membership.refunded_cents)} Tier Refund, so you paid ${net}.`;
  }
  if (membership.status === "charged") return `You are a Member. You were charged ${charged}.`;
  if (status === "locked") return "You are a Member. Your charge is being processed.";
  return "You are a Member. Your card is saved and you won't be charged until this Pool Locks.";
}
