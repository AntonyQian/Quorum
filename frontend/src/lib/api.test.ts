import { describe, expect, test } from "vitest";
import { ApiError, createApi } from "./api";

const baseUrl = "http://localhost:8000";

function mockApi() {
  const fetchImpl: typeof fetch = () => {
    throw new Error("mocks must not call the network");
  };
  return createApi({
    useMocks: true,
    baseUrl,
    getUserId: () => "1",
    fetch: fetchImpl,
  });
}

describe("mock API client", () => {
  test("lists switcher accounts and hides Simulated Shoppers", async () => {
    const users = await mockApi().listUsers();
    expect(users.map((user) => user.name)).toEqual([
      "Alice",
      "Bob",
      "Oak & Co.",
      "Nordlund",
      "ReLoft",
    ]);
    expect(users.every((user) => user.is_simulated === false)).toBe(true);

    const withSimulated = await mockApi().listUsers({ includeSimulated: true });
    expect(withSimulated.some((user) => user.is_simulated)).toBe(true);
  });

  test("returns Pool summaries in every state, filtered by status and category", async () => {
    const api = mockApi();
    const live = await api.listPools({ status: "open,locked" });
    expect(live.map((pool) => pool.status).sort()).toEqual([
      "locked",
      "open",
      "open",
      "open",
    ]);
    const sofas = await api.listPools({ category: "sofa" });
    expect(sofas).toHaveLength(1);
    expect(sofas[0]?.product.name).toBe("Cloud Sofa");
    expect(sofas[0]?.current_price_cents).toBe(180000);
    expect(sofas[0]?.participants).toBe(4);
    expect(sofas[0]?.time_left_seconds).toBe(3600);

    const failed = await api.listPools({ status: "failed" });
    expect(failed.map((pool) => pool.status)).toEqual(["failed"]);
    const completed = await api.listPools({ status: "completed" });
    expect(completed[0]?.product.name).toBe("Oak Dresser");
  });

  test("returns a Pool detail in the SPEC shape", async () => {
    const detail = await mockApi().getPool(1);
    expect(detail.product.description).toContain("maple");
    expect(detail.product.dimensions).toBe("60 in wide, seats 4");
    expect(detail.my_membership).toBeNull();
    expect(detail.final_price_cents).toBeNull();
    expect(detail.next_tier).toEqual({
      ordinal: 1,
      needed: 2,
      price_cents: 64000,
    });
    expect(detail.tiers[0]?.price_cents).toBe(64000);
  });

  test("a missing Pool is a not_found error", async () => {
    await expect(mockApi().getPool(99)).rejects.toMatchObject({
      name: "ApiError",
      code: "not_found",
    });
  });

  test("covers orders, notifications, recommendations, retailer, and the Sim Clock", async () => {
    const api = mockApi();
    const orders = await api.listOrders();
    expect(orders[0]?.payments.map((payment) => payment.kind)).toEqual([
      "charge",
      "refund",
    ]);
    expect(orders[0]?.net_paid_cents).toBe(74000);

    const notifications = await api.listNotifications();
    expect(notifications.unread).toBe(1);
    expect(notifications.items[0]?.link).toBe("/pools/3");

    const recommendation = await api.recommend("walnut dining table");
    expect(recommendation.recommendations[0]?.fit_score).toBe(91);
    expect(recommendation.parsed.category).toBe("dining_table");

    const products = await api.listRetailerProducts();
    const hidden = products.find((product) => product.visibility === "hidden");
    expect(hidden?.name).toBe("Walnut Dining Table");
    expect(hidden?.demand).toEqual({
      total_hits: 9,
      last_7_days: 4,
      threshold: 10,
      threshold_reached: false,
    });
    expect(hidden?.pool).toBeNull();

    const demand = await api.getDemand(31);
    expect(demand.total_hits).toBe(9);
    expect(demand.recent_wishes[0]?.text).toBe("walnut dining table for 4");

    const retailerPool = await api.getRetailerPool(3);
    expect(retailerPool.revenue_cents).toBe(444000);
    expect(retailerPool.members[0]?.status).toBe("charged");

    expect(await api.getClock()).toEqual({ now: "2026-10-17T21:00:00Z" });
    expect(await api.createSetupSession()).toEqual({
      url: "http://localhost:3000/payment/success?session_id=mock_1",
    });
    expect(await api.confirmSetup("mock_1")).toEqual({
      card_label: "Visa •••• 4242",
    });
  });
});

describe("live API client", () => {
  test("sends X-User-Id to NEXT_PUBLIC_API_URL", async () => {
    const calls: { url: string; userId: string | null; method: string }[] = [];
    const api = createApi({
      useMocks: false,
      baseUrl,
      getUserId: () => "7",
      fetch: async (url, init) => {
        const headers = new Headers(init?.headers);
        calls.push({
          url: String(url),
          userId: headers.get("X-User-Id"),
          method: init?.method ?? "GET",
        });
        return new Response(JSON.stringify([]), { status: 200 });
      },
    });

    await api.listUsers();
    await api.listPools({ status: "open,locked", category: "sofa" });
    expect(calls).toEqual([
      { url: `${baseUrl}/api/users`, userId: "7", method: "GET" },
      {
        url: `${baseUrl}/api/pools?status=open%2Clocked&category=sofa`,
        userId: "7",
        method: "GET",
      },
    ]);
  });

  test("surfaces card_required from the error body", async () => {
    const api = createApi({
      useMocks: false,
      baseUrl,
      getUserId: () => "1",
      fetch: async () =>
        new Response(
          JSON.stringify({
            detail: { code: "card_required", message: "Save a card to Join." },
          }),
          { status: 402 },
        ),
    });

    await expect(api.joinPool(1)).rejects.toBeInstanceOf(ApiError);
    await expect(api.joinPool(1)).rejects.toMatchObject({
      code: "card_required",
      message: "Save a card to Join.",
    });
  });
});
