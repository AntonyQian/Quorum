"use client";

import { useState, type FormEvent } from "react";
import { flushSync } from "react-dom";
import { PoolBrowser } from "@/components/pool-browser";
import { PoolCard } from "@/components/pool-card";
import { Button } from "@/components/ui/button";
import { layout, memberPanel, skeleton, typeScale } from "@/design/tokens";
import { ApiError, api } from "@/lib/api";
import type { RecommendResponse } from "@/lib/types";
import { cn } from "cn";

type HomeMode = "browse" | "wish";

function formatBudget(cents: number | null): string | null {
  if (cents == null) return null;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

function ParsedSummary({ parsed }: { parsed: RecommendResponse["parsed"] }) {
  const budget = formatBudget(parsed.budget_max_cents);
  const parts = [
    parsed.category?.replace(/_/g, " "),
    budget ? `under ${budget}` : null,
    parsed.size_notes || null,
    parsed.style_tags.length ? parsed.style_tags.join(", ") : null,
  ].filter(Boolean);

  if (parts.length === 0) return null;

  return (
    <p className={typeScale.meta}>
      Your specs:{" "}
      <span className="font-medium text-foreground">{parts.join(" · ")}</span>
    </p>
  );
}

function SearchSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-hidden>
      <div className={`${skeleton} h-5 w-64`} />
      <div className={layout.grid}>
        <div className={`${skeleton} h-80`} />
        <div className={`${skeleton} h-80`} />
      </div>
    </div>
  );
}

export function ShopperHome() {
  const [mode, setMode] = useState<HomeMode>("browse");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendResponse | null>(null);

  const recommendations = result?.recommendations ?? [];
  const suggestions = result?.suggestions ?? [];
  const hasRecs = recommendations.length > 0;
  const hasSuggestions = suggestions.length > 0;

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = query.trim();
    if (!text) return;

    flushSync(() => {
      setMode("wish");
      setBusy(true);
      setError(null);
      setResult(null);
    });

    try {
      setResult(await api.recommend(text));
    } catch (err) {
      setResult(null);
      setMode("browse");
      setError(
        err instanceof ApiError && err.code === "recommender_unavailable"
          ? "The recommender is unavailable right now. Browse the Pools below."
          : "Couldn't get recommendations. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  function returnToBrowse() {
    setMode("browse");
    setResult(null);
    setError(null);
  }

  return (
    <div className={cn(layout.stack, "gap-10")}>
      <section className="flex flex-col gap-4">
        <form onSubmit={submit} className="flex flex-col gap-3">
          <h1 className={typeScale.display}>What are you looking for?</h1>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="A walnut dining table for six, under $1,200"
              aria-label="Describe what you want"
              className="h-10 flex-1 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            />
            <Button type="submit" size="lg" disabled={busy || !query.trim()}>
              {busy ? "Finding..." : "Find it"}
            </Button>
          </div>
        </form>

        {error ? <p className={memberPanel.error} role="alert">{error}</p> : null}

        {mode === "wish" ? (
          <div
            className="flex flex-col gap-6 rounded-xl border border-border bg-card/40 p-5 sm:p-6"
            aria-label="Search results"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-col gap-1">
                <h2 className={typeScale.display}>Search results</h2>
                {busy ? (
                  <p className={typeScale.meta} aria-live="polite">
                    Matching live Pools to your Wish…
                  </p>
                ) : result ? (
                  <ParsedSummary parsed={result.parsed} />
                ) : null}
              </div>
              {!busy && result ? (
                <Button type="button" variant="outline" size="sm" onClick={returnToBrowse}>
                  Back to all Pools
                </Button>
              ) : null}
            </div>

            {busy ? (
              <SearchSkeleton />
            ) : result ? (
              <>
                {hasRecs ? (
                  <div className="flex flex-col gap-3">
                    <h3 className={typeScale.title}>Matches for your Wish</h3>
                    <div className={layout.grid}>
                      {recommendations.map((rec) => (
                        <PoolCard key={rec.pool.id} pool={rec.pool} />
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    <h3 className={typeScale.title}>We didn&apos;t find live Pools under your specs</h3>
                    <p className={typeScale.meta}>
                      Nothing on Quorum right now fits every constraint you gave. We saved your Wish so
                      Retailers can see the demand.
                    </p>
                  </div>
                )}

                {hasSuggestions ? (
                  <div className="flex flex-col gap-3 border-t border-border pt-6">
                    <h3 className={typeScale.title}>You might also like</h3>
                    <p className={typeScale.meta}>
                      {hasRecs
                        ? "These are close, but they miss part of what you asked for."
                        : "These Pools are nearby — they may be over budget or a different fit."}
                    </p>
                    <div className={layout.grid}>
                      {suggestions.map((rec) => (
                        <PoolCard key={rec.pool.id} pool={rec.pool} />
                      ))}
                    </div>
                  </div>
                ) : null}

                {!hasRecs && !hasSuggestions ? (
                  <p className={typeScale.meta}>
                    Try broadening your budget or category, or check back when new Pools open.
                  </p>
                ) : null}
              </>
            ) : null}
          </div>
        ) : null}
      </section>

      {mode === "browse" ? <PoolBrowser /> : null}
    </div>
  );
}
