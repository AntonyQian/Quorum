import { describe, expect, test } from "vitest";
import { joinAction, membershipMessage } from "./membership";
import type { Membership, PoolStatus } from "./types";

function pool(
  status: PoolStatus,
  my_membership: Membership | null,
  next_tier: { needed: number; price_cents: number } | null = null,
) {
  return { status, my_membership, current_price_cents: 64000, next_tier };
}

const pending: Membership = { status: "pending", charged_cents: 0, refunded_cents: 0 };
const charged: Membership = { status: "charged", charged_cents: 64000, refunded_cents: 0 };

describe("Join and Leave", () => {
  test("an open Pool offers a free Join, and Leave once you are a Member", () => {
    expect(joinAction(pool("open", null))).toEqual({ kind: "join", label: "Join" });
    expect(joinAction(pool("open", pending))).toEqual({ kind: "leave", label: "Leave" });
  });

  test("a locked Pool says what Joining charges now", () => {
    expect(joinAction(pool("locked", null))).toEqual({
      kind: "join",
      label: "Join (you'll be charged $640.00 now)",
    });
  });

  test("Joining a locked Pool one Member short of the next Tier charges the next Tier price", () => {
    expect(joinAction(pool("locked", null, { needed: 1, price_cents: 55000 }))).toEqual({
      kind: "join",
      label: "Join (you'll be charged $550.00 now)",
    });
    expect(joinAction(pool("locked", null, { needed: 2, price_cents: 55000 }))).toEqual({
      kind: "join",
      label: "Join (you'll be charged $640.00 now)",
    });
  });

  test("a Member of a locked Pool can't Leave", () => {
    expect(joinAction(pool("locked", charged))).toEqual({ kind: "none" });
  });

  test("a Member who left or whose card was declined can Join again", () => {
    const left: Membership = { ...pending, status: "left" };
    const declined: Membership = { ...pending, status: "payment_failed" };
    expect(joinAction(pool("open", left)).kind).toBe("join");
    expect(joinAction(pool("locked", declined)).kind).toBe("join");
  });

  test("settled Pools take no new Members", () => {
    expect(joinAction(pool("completed", null))).toEqual({ kind: "none" });
    expect(joinAction(pool("failed", null))).toEqual({ kind: "none" });
  });
});

describe("the Member's line on a Pool", () => {
  test("is empty for a Shopper who never joined", () => {
    expect(membershipMessage("open", null)).toBeNull();
  });

  test("tells a pending Member they pay nothing until Lock", () => {
    expect(membershipMessage("open", pending)).toBe(
      "You are a Member. Your card is saved and you won't be charged until this Pool Locks.",
    );
  });

  test("shows what a Member was charged once the Pool Locks", () => {
    expect(membershipMessage("locked", charged)).toBe(
      "You are a Member. You were charged $640.00.",
    );
  });

  test("shows the charge, the Tier Refund and the net once the Pool completes", () => {
    expect(
      membershipMessage("completed", { status: "charged", charged_cents: 64000, refunded_cents: 9000 }),
    ).toBe("You were charged $640.00 and got a $90.00 Tier Refund, so you paid $550.00.");
    expect(membershipMessage("completed", charged)).toBe("You paid $640.00.");
  });

  test("reassures a Member of a Failed Pool and explains a declined card", () => {
    expect(membershipMessage("failed", pending)).toBe("You were not charged.");
    expect(
      membershipMessage("locked", { status: "payment_failed", charged_cents: 0, refunded_cents: 0 }),
    ).toBe("Your card was declined, so you are no longer a Member. Save another card to Join again.");
    expect(membershipMessage("open", { ...pending, status: "left" })).toBe("You left this Pool.");
  });
});
