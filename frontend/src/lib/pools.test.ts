import { describe, expect, test } from "vitest";
import {
  discountOffer,
  filterPoolsByCategory,
  formatSimClock,
  formatTimeLeft,
  formatTimeLeftWords,
  poolProgressCaption,
  tierProgress,
} from "./pools";

describe("Pool display", () => {
  test("formats a countdown from time_left_seconds", () => {
    expect(formatTimeLeft(172800)).toBe("2d 0h");
    expect(formatTimeLeft(3600)).toBe("1h 0m");
    expect(formatTimeLeft(90)).toBe("1m");
    expect(formatTimeLeft(45)).toBe("45s");
    expect(formatTimeLeft(0)).toBe("Ended");
  });

  test("spells a card Deadline in words", () => {
    expect(formatTimeLeftWords(86400)).toBe("1 day");
    expect(formatTimeLeftWords(172800)).toBe("2 days");
    expect(formatTimeLeftWords(3600)).toBe("1 hour");
    expect(formatTimeLeftWords(500000)).toBe("5 days 18 hours");
    expect(formatTimeLeftWords(0)).toBe("Ended");
  });

  test("formats the Sim Clock from the API timestamp", () => {
    expect(formatSimClock("2026-10-17T21:00:00Z")).toBe(
      "Oct 17, 2026, 9:00 PM UTC",
    );
  });

  test("shows the next discount when none is in effect yet", () => {
    const offer = discountOffer({
      status: "open",
      participants: 8,
      current_price_cents: 64000,
      next_tier: { needed: 2, price_cents: 64000 },
      tiers: [
        { min_participants: 10, reached: false },
        { min_participants: 25, reached: false },
      ],
      product: { list_price_cents: 80000 },
    });
    expect(offer.active).toBeNull();
    expect(offer.next).toEqual({ needed: 2, priceCents: 64000 });
    expect(offer.label).toBe("2 more Members");
    expect(offer.progressPercent).toBe(80);
  });

  test("keeps the next price when a discount is already in effect", () => {
    const offer = discountOffer({
      status: "locked",
      participants: 12,
      current_price_cents: 37000,
      next_tier: { needed: 8, price_cents: 31000 },
      tiers: [
        { min_participants: 10, reached: true },
        { min_participants: 20, reached: false },
      ],
      product: { list_price_cents: 45000 },
    });
    expect(offer.active).toEqual({ priceCents: 37000, savingsCents: 8000 });
    expect(offer.next).toEqual({ needed: 8, priceCents: 31000 });
    expect(offer.progressPercent).toBe(60);
  });

  test("fills the bar when the top Tier is reached and stays quiet when a Pool fails", () => {
    expect(
      discountOffer({
        status: "completed",
        participants: 18,
        current_price_cents: 74000,
        next_tier: null,
        tiers: [{ min_participants: 16, reached: true }],
        product: { list_price_cents: 96000 },
      }),
    ).toMatchObject({
      active: { priceCents: 74000, savingsCents: 22000 },
      next: null,
      progressPercent: 100,
      label: "Settled",
    });
    expect(
      discountOffer({
        status: "failed",
        participants: 3,
        current_price_cents: 15000,
        next_tier: { needed: 7, price_cents: 15000 },
        tiers: [{ min_participants: 10, reached: false }],
        product: { list_price_cents: 18000 },
      }),
    ).toMatchObject({
      active: null,
      next: null,
      progressPercent: 30,
      label: "This Pool didn't reach Tier 1",
    });
  });

  test("says how many people the next Tier needs", () => {
    expect(poolProgressCaption({ status: "open", next_tier: { needed: 2 } })).toBe(
      "Next tier in 2 people",
    );
    expect(
      poolProgressCaption({ status: "locked", next_tier: { needed: 8 } }),
    ).toBe("Next tier in 8 people");
    expect(poolProgressCaption({ status: "locked", next_tier: null })).toBe(
      "Top Tier reached",
    );
    expect(poolProgressCaption({ status: "failed", next_tier: { needed: 7 } })).toBe(
      "This Pool didn't reach Tier 1",
    );
    expect(poolProgressCaption({ status: "completed", next_tier: null })).toBe(
      "Settled",
    );
  });

  test("places a marker on each Tier and fills to the Member count", () => {
    const progress = tierProgress({
      participants: 8,
      stock_cap: null,
      tiers: [
        { ordinal: 1, min_participants: 10, reached: false },
        { ordinal: 2, min_participants: 25, reached: false },
      ],
    });
    expect(progress.fillPercent).toBe(32);
    expect(progress.markers.map((marker) => marker.percent)).toEqual([40, 100]);
    expect(progress.markers.map((marker) => marker.reached)).toEqual([
      false,
      false,
    ]);
  });

  test("category chips keep only that category", () => {
    const pools = [
      { product: { category: "sofa" } },
      { product: { category: "dining_table" } },
    ];
    expect(filterPoolsByCategory(pools, null)).toHaveLength(2);
    expect(filterPoolsByCategory(pools, "sofa")).toEqual([
      { product: { category: "sofa" } },
    ]);
  });
});
