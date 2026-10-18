"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAccount } from "@/components/account-provider";
import { Button } from "@/components/ui/button";
import { memberPanel, textLink, typeScale } from "@/design/tokens";
import { api } from "@/lib/api";
import { finishCardFlow } from "@/lib/card-flow";
import { friendlyError } from "@/lib/errors";

/** Confirms the saved card, finishes the Join that started the flow, then returns to the Pool. */
export function PaymentSuccess() {
  const { ready } = useAccount();
  const router = useRouter();
  const sessionId = useSearchParams().get("session_id");
  const [message, setMessage] = useState("Saving your card…");
  const [error, setError] = useState<string | null>(null);
  const [returnTo, setReturnTo] = useState("/");
  const started = useRef(false);
  // Mock mode has no hosted card page, so show a stand-in card form first.
  const isMock = sessionId?.startsWith("mock_") ?? false;
  const [cardEntered, setCardEntered] = useState(false);

  useEffect(() => {
    // Wait for the account, so the card is saved for the Shopper who started the flow.
    if (!ready || started.current || (isMock && !cardEntered)) return;
    started.current = true;
    const flow = finishCardFlow(window.sessionStorage);
    setReturnTo(flow.returnTo);

    async function finish() {
      if (!sessionId) {
        setError("This link is missing its card-saving session.");
        return;
      }
      try {
        const { card_label } = await api.confirmSetup(sessionId);
        setMessage(`Saved ${card_label}.`);
      } catch (err) {
        setError(friendlyError(err));
        return;
      }
      if (flow.joinPoolId != null) {
        setMessage("Card saved. Joining the Pool…");
        try {
          await api.joinPool(flow.joinPoolId);
        } catch (err) {
          setError(`Your card is saved, but the Join didn't go through: ${friendlyError(err)}`);
          return;
        }
      }
      router.replace(flow.returnTo);
    }

    void finish();
  }, [ready, sessionId, router, isMock, cardEntered]);

  if (isMock && !cardEntered) {
    return (
      <section className="flex max-w-sm flex-col gap-3">
        <h1 className={typeScale.display}>Add a card</h1>
        <p className={typeScale.meta}>Test mode: this stands in for the Stripe card page.</p>
        <input
          readOnly
          aria-label="Card number"
          className="h-9 rounded-lg border border-input bg-background px-3 text-sm"
          value="4242 4242 4242 4242"
        />
        <div className="flex gap-2">
          <input readOnly aria-label="Expiry" className="h-9 w-24 rounded-lg border border-input bg-background px-3 text-sm" value="12 / 34" />
          <input readOnly aria-label="CVC" className="h-9 w-20 rounded-lg border border-input bg-background px-3 text-sm" value="123" />
        </div>
        <Button size="lg" className="self-start" onClick={() => setCardEntered(true)}>
          Save card
        </Button>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-3">
      <h1 className={typeScale.display}>Your card</h1>
      {error ? (
        <>
          <p className={memberPanel.error} role="alert">
            {error}
          </p>
          <Link href={returnTo} className={textLink}>
            Back to the Pool
          </Link>
        </>
      ) : (
        <p className={typeScale.meta} aria-live="polite">
          {message}
        </p>
      )}
    </section>
  );
}
