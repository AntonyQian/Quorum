import { describe, expect, test } from "vitest";
import { totalSavingsCents } from "./orders";

function order(listCents: number, netPaidCents: number) {
  return { product: { list_price_cents: listCents }, net_paid_cents: netPaidCents };
}

describe("My Orders savings", () => {
  test("adds up list price minus net paid on every order the Shopper paid for", () => {
    // $1,399 sofa settled at $1,099 after a Tier Refund, $899 shelf charged $799.
    expect(totalSavingsCents([order(139900, 109900), order(89900, 79900)])).toBe(40000);
  });

  test("leaves out orders nothing was paid for: pending, left, declined, or a Failed Pool", () => {
    expect(totalSavingsCents([order(139900, 0), order(89900, 79900)])).toBe(10000);
    expect(totalSavingsCents([])).toBe(0);
  });
});
