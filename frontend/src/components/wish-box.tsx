"use client";

import { useState } from "react";
import { PoolCard } from "@/components/pool-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { layout, memberPanel, typeScale } from "@/design/tokens";
import { ApiError, api } from "@/lib/api";
import type { RecommendResponse } from "@/lib/types";

export function WishBox() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendResponse | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.recommend(text.trim()));
    } catch (err) {
      setResult(null);
      setError(
        err instanceof ApiError && err.code === "recommender_unavailable"
          ? "The recommender is unavailable right now. Browse the Pools below."
          : "Couldn't get recommendations. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <form onSubmit={submit} className="flex flex-col gap-3">
        <h1 className={typeScale.display}>What are you looking for?</h1>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="A walnut dining table for six, under $1,200"
            aria-label="Describe what you want"
            className="h-10 flex-1 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          <Button type="submit" size="lg" disabled={busy || !text.trim()}>
            {busy ? "Finding..." : "Find it"}
          </Button>
        </div>
      </form>
      {error ? <p className={memberPanel.error} role="alert">{error}</p> : null}
      {result ? (
        result.recommendations.length === 0 ? (
          <p className={typeScale.meta}>
            Nothing live matches yet. We saved your Wish, and the Retailer will see the demand.
          </p>
        ) : (
          <div className={layout.grid}>
            {result.recommendations.map((rec) => (
              <div key={rec.pool.id} className="flex flex-col gap-2">
                <PoolCard pool={rec.pool} />
                <div className="flex items-start gap-2">
                  <Badge variant="secondary">{rec.fit_score}% fit</Badge>
                  <p className={typeScale.meta}>{rec.reason}</p>
                </div>
              </div>
            ))}
          </div>
        )
      ) : null}
    </section>
  );
}
