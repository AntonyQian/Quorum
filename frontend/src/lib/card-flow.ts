export const CARD_FLOW_STORAGE_KEY = "quorum-card-flow";

export type CardFlow = { returnTo: string; joinPoolId: number | null };

export type CardFlowStore = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
};

/** Only paths inside this app, so a stored value can't send the Shopper elsewhere. */
function safePath(path: unknown): string {
  return typeof path === "string" && path.startsWith("/") && !path.startsWith("//")
    ? path
    : "/";
}

/** Called before leaving for the card-saving page; the success URL carries only the session id. */
export function startCardFlow(store: CardFlowStore, flow: CardFlow): void {
  store.setItem(CARD_FLOW_STORAGE_KEY, JSON.stringify(flow));
}

/** Reads and forgets the pending flow, so a reload of the success page doesn't Join twice. */
export function finishCardFlow(store: CardFlowStore): CardFlow {
  const raw = store.getItem(CARD_FLOW_STORAGE_KEY);
  store.removeItem(CARD_FLOW_STORAGE_KEY);
  try {
    const parsed = JSON.parse(raw ?? "null") as Partial<CardFlow> | null;
    return {
      returnTo: safePath(parsed?.returnTo),
      joinPoolId: typeof parsed?.joinPoolId === "number" ? parsed.joinPoolId : null,
    };
  } catch {
    return { returnTo: "/", joinPoolId: null };
  }
}
