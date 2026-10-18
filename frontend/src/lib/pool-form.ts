import { dollarsToCents } from "./money";
import type { PoolCreate } from "./types";

export type TierRow = { min: string; discount: string };

export type PoolFormState = {
  deadlineDays: number;
  stockCap: string;
  tiers: TierRow[];
};

export const emptyPoolForm: PoolFormState = {
  deadlineDays: 14,
  stockCap: "",
  tiers: [{ min: "10", discount: "100" }],
};

export const MAX_TIERS = 3;

/** The PoolCreate body for the form, or the first thing wrong with it. */
export function buildPoolCreate(
  form: PoolFormState,
  prices: { listCents: number; floorCents: number },
): { pool: PoolCreate } | { error: string } {
  const tiers: PoolCreate["tiers"] = [];
  for (const [index, row] of form.tiers.entries()) {
    const min = Number(row.min);
    const discount = dollarsToCents(row.discount);
    if (!Number.isInteger(min) || min < 1 || discount == null || discount < 1) {
      return { error: `Tier ${index + 1} needs a Member count and a discount.` };
    }
    const prev = tiers[index - 1];
    if (prev && (min <= prev.min_participants || discount <= prev.discount_cents)) {
      return { error: "Each Tier needs more Members and a bigger discount than the one before." };
    }
    if (prices.listCents - discount < prices.floorCents) {
      return { error: `Tier ${index + 1} would price below the Floor Price.` };
    }
    tiers.push({ min_participants: min, discount_cents: discount });
  }
  let stockCap: number | null = null;
  if (form.stockCap.trim()) {
    stockCap = Number(form.stockCap);
    if (!Number.isInteger(stockCap) || stockCap < 1) return { error: "Stock cap must be a whole number." };
  }
  return { pool: { deadline_days: form.deadlineDays, stock_cap: stockCap, tiers } };
}
