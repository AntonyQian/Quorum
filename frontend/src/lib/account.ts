import type { UserRole } from "./types";

export const USER_ID_STORAGE_KEY = "quorum-user-id";

export type UserIdStore = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
};

export function readSelectedUserId(store: UserIdStore): string | null {
  return store.getItem(USER_ID_STORAGE_KEY);
}

export function writeSelectedUserId(store: UserIdStore, userId: string): void {
  store.setItem(USER_ID_STORAGE_KEY, userId);
}

/** Keeps a stored id that still exists; otherwise the first Shopper, then the first account. */
export function resolveSelectedUserId(
  stored: string | null,
  users: { id: number; role?: UserRole }[],
): string | null {
  if (stored && users.some((user) => String(user.id) === stored)) return stored;
  const first = users.find((user) => user.role === "shopper") ?? users[0];
  return first ? String(first.id) : null;
}

let activeUserId = "1";

export function getActiveUserId(): string {
  return activeUserId;
}

export function setActiveUserId(userId: string): void {
  activeUserId = userId;
}

export function hydrateActiveUserId(store: UserIdStore): void {
  const stored = readSelectedUserId(store);
  if (stored) activeUserId = stored;
}
