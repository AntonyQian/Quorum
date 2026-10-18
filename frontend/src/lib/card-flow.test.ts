import { describe, expect, test } from "vitest";
import { ApiError } from "./api";
import { finishCardFlow, startCardFlow } from "./card-flow";
import { friendlyError } from "./errors";

function memoryStore() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => void values.set(key, value),
    removeItem: (key: string) => void values.delete(key),
  };
}

describe("friendly error messages", () => {
  test("turn SPEC error codes into sentences a Shopper understands", () => {
    expect(friendlyError(new ApiError("cannot_leave_locked", "x"))).toBe(
      "This Pool has Locked, so Members can't Leave.",
    );
    expect(friendlyError(new ApiError("stock_cap_reached", "x"))).toBe(
      "This Pool is full.",
    );
    expect(friendlyError(new ApiError("pool_not_joinable", "x"))).toBe(
      "This Pool isn't taking new Members.",
    );
  });

  test("fall back to the server message, then to a generic one", () => {
    expect(friendlyError(new ApiError("something_new", "Try later"))).toBe("Try later");
    expect(friendlyError(new TypeError("Failed to fetch"))).toBe(
      "Something went wrong. Try again.",
    );
  });
});

describe("card-saving flow", () => {
  test("remembers where to return and which Pool to Join after the card is saved", () => {
    const store = memoryStore();
    startCardFlow(store, { returnTo: "/pools/7", joinPoolId: 7 });
    expect(finishCardFlow(store)).toEqual({ returnTo: "/pools/7", joinPoolId: 7 });
  });

  test("is forgotten once finished, so a reload doesn't Join twice", () => {
    const store = memoryStore();
    startCardFlow(store, { returnTo: "/pools/7", joinPoolId: 7 });
    finishCardFlow(store);
    expect(finishCardFlow(store)).toEqual({ returnTo: "/", joinPoolId: null });
  });

  test("ignores a stored value that isn't ours and only returns to a path in this app", () => {
    const store = memoryStore();
    store.setItem("quorum-card-flow", "not json");
    expect(finishCardFlow(store)).toEqual({ returnTo: "/", joinPoolId: null });
    startCardFlow(store, { returnTo: "https://evil.example", joinPoolId: null });
    expect(finishCardFlow(store).returnTo).toBe("/");
    startCardFlow(store, { returnTo: "//evil.example", joinPoolId: null });
    expect(finishCardFlow(store).returnTo).toBe("/");
  });
});
