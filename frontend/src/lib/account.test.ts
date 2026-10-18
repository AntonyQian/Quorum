import { describe, expect, test } from "vitest";
import {
  USER_ID_STORAGE_KEY,
  getActiveUserId,
  hydrateActiveUserId,
  readSelectedUserId,
  resolveSelectedUserId,
  setActiveUserId,
  writeSelectedUserId,
} from "./account";

function memoryStore() {
  const values = new Map<string, string>();
  return {
    getItem(key: string) {
      return values.get(key) ?? null;
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
  };
}

describe("account selection", () => {
  test("remembers the selected account", () => {
    const store = memoryStore();
    expect(readSelectedUserId(store)).toBeNull();
    writeSelectedUserId(store, "2");
    expect(readSelectedUserId(store)).toBe("2");
    expect(store.getItem(USER_ID_STORAGE_KEY)).toBe("2");
  });

  test("keeps a stored id that still exists, otherwise the first account", () => {
    const users = [{ id: 1 }, { id: 2 }];
    expect(resolveSelectedUserId("2", users)).toBe("2");
    expect(resolveSelectedUserId("99", users)).toBe("1");
    expect(resolveSelectedUserId(null, users)).toBe("1");
    expect(resolveSelectedUserId(null, [])).toBeNull();
  });

  test("with nothing stored, starts as the first Shopper rather than a Retailer", () => {
    const users = [
      { id: 1, role: "retailer" as const },
      { id: 4, role: "shopper" as const },
      { id: 5, role: "shopper" as const },
    ];
    expect(resolveSelectedUserId(null, users)).toBe("4");
    expect(resolveSelectedUserId("99", users)).toBe("4");
    expect(resolveSelectedUserId("1", users)).toBe("1");
  });

  test("requests use the active account, restored from storage", () => {
    setActiveUserId("4");
    expect(getActiveUserId()).toBe("4");
    const store = memoryStore();
    writeSelectedUserId(store, "2");
    hydrateActiveUserId(store);
    expect(getActiveUserId()).toBe("2");
  });
});
