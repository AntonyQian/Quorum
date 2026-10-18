"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useAccount } from "@/components/account-provider";
import { memberPanel, typeScale } from "@/design/tokens";
import { ApiError, api } from "@/lib/api";
import { startCardFlow } from "@/lib/card-flow";
import { friendlyError } from "@/lib/errors";
import { joinAction, membershipMessage } from "@/lib/membership";
import type { PoolDetail } from "@/lib/types";

/** Join or Leave, the card-saving redirect, and the active account's Member line. */
export function JoinPanel({
  pool,
  onChange,
}: {
  pool: PoolDetail;
  onChange: (pool: PoolDetail) => void;
}) {
  const { user } = useAccount();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const action = joinAction(pool);
  const line = membershipMessage(pool.status, pool.my_membership);
  const isRetailer = user?.role === "retailer";

  async function saveCardThenJoin() {
    const returnTo = `/pools/${pool.id}`;
    startCardFlow(window.sessionStorage, { returnTo, joinPoolId: pool.id });
    const { url } = await api.createSetupSession(returnTo);
    window.location.assign(url);
  }

  async function run() {
    if (action.kind === "none") return;
    setBusy(true);
    setError(null);
    try {
      if (action.kind === "join") {
        onChange(await api.joinPool(pool.id));
      } else {
        onChange(await api.leavePool(pool.id));
      }
      setBusy(false);
    } catch (err) {
      if (err instanceof ApiError && err.code === "card_required") {
        try {
          await saveCardThenJoin();
          return; // The browser is leaving for the card-saving page.
        } catch (setupError) {
          setError(friendlyError(setupError));
        }
      } else {
        setError(friendlyError(err));
      }
      setBusy(false);
    }
  }

  if (!line && action.kind === "none") return null;

  return (
    <section className={memberPanel.box} aria-live="polite">
      {line ? <p className={memberPanel.line}>{line}</p> : null}
      {action.kind !== "none" ? (
        isRetailer ? (
          <p className={typeScale.meta}>Switch to a Shopper account to Join.</p>
        ) : (
          <div className="flex flex-col items-start gap-2">
            <Button
              size="lg"
              variant={action.kind === "leave" ? "outline" : "default"}
              disabled={busy}
              onClick={() => void run()}
            >
              {busy ? "Working…" : action.label}
            </Button>
            {action.kind === "join" && pool.status === "open" ? (
              <p className={typeScale.meta}>
                Free until this Pool Locks. You can Leave any time before then.
              </p>
            ) : null}
          </div>
        )
      ) : null}
      {error ? (
        <p className={memberPanel.error} role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
