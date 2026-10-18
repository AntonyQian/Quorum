import { ApiError } from "./api";

const messages: Record<string, string> = {
  pool_not_joinable: "This Pool isn't taking new Members.",
  already_member: "You are already a Member of this Pool.",
  stock_cap_reached: "This Pool is full.",
  not_member: "You aren't a Member of this Pool.",
  cannot_leave_locked: "This Pool has Locked, so Members can't Leave.",
  card_required: "Save a card to Join this Pool.",
  not_found: "This Pool is not available.",
  forbidden: "Pick an account in the top bar first.",
};

/** A sentence for the Shopper from a SPEC §3 error code. */
export function friendlyError(error: unknown): string {
  if (error instanceof ApiError) {
    return messages[error.code] ?? (error.message || "Something went wrong. Try again.");
  }
  return "Something went wrong. Try again.";
}
