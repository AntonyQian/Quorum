"use client";

import { Loader2, Search } from "lucide-react";
import { PoolBrowser } from "@/components/pool-browser";
import { PoolCard } from "@/components/pool-card";
import { layout, memberPanel, skeleton, typeScale } from "@/design/tokens";
import Link from "next/link";
import type { RecommendResponse } from "@/lib/types";
import { cn } from "cn";

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
        <div className={`${skeleton} h-52`} />
        <div className={`${skeleton} h-52`} />
      </div>
    </div>
  );
}

type HomeSceneProps = {
  query: string;
  mode: "browse" | "wish";
  busy: boolean;
  result: RecommendResponse | null;
  showCaret: boolean;
};

export function VideoDemoHomeScene({
  query,
  mode,
  busy,
  result,
  showCaret,
}: HomeSceneProps) {
  const recommendations = result?.recommendations ?? [];
  const hasRecs = recommendations.length > 0;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="shrink-0 border-b bg-background/90 backdrop-blur-md">
        <div className="mx-auto flex h-11 w-full max-w-6xl items-center gap-2 px-3">
          <Link href="/" className={typeScale.wordmark}>
            Quorum
          </Link>
        </div>
      </header>
      <div className={cn(layout.stack, "min-h-0 flex-1 gap-6 overflow-hidden px-3 py-4")}>
      <section
        className={cn(
          "mx-auto flex w-full max-w-xl shrink-0 flex-col items-center gap-5 text-center transition-all duration-700 ease-out",
          mode === "browse" ? "mt-[8vh]" : "mt-3",
        )}
      >
        <h1 className="font-heading text-2xl font-medium tracking-tight text-balance sm:text-[1.75rem]">
          What are you looking for?
        </h1>
        <div className="relative w-full">
          <div
            className={cn(
              "absolute top-1/2 right-1.5 flex size-9 -translate-y-1/2 items-center justify-center rounded-full",
              "bg-primary text-primary-foreground",
            )}
          >
            {busy ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Search className="size-4" aria-hidden />
            )}
          </div>
          <div
            className="flex h-12 w-full items-center rounded-full border border-input bg-background py-2 pr-12 pl-4 text-left text-sm"
            aria-label="Describe what you want"
          >
            <span className="truncate text-foreground">{query}</span>
            {showCaret ? (
              <span className="ml-0.5 inline-block h-[1.1em] w-px animate-pulse bg-foreground" />
            ) : null}
          </div>
        </div>
      </section>

      {mode === "wish" ? (
        <section
          className={cn(
            "min-h-0 flex-1 overflow-hidden opacity-100 transition-all duration-700",
            "animate-in fade-in slide-in-from-bottom-3",
          )}
        >
          <div
            className="flex h-full flex-col gap-4 overflow-hidden rounded-xl border border-border bg-card/40 p-5 sm:p-6"
            aria-label="Search results"
          >
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

            {busy ? (
              <SearchSkeleton />
            ) : result ? (
              <>
                {hasRecs ? (
                  <div className="flex min-h-0 flex-col gap-3">
                    <h3 className={typeScale.title}>Matches for your Wish</h3>
                    <div className={cn(layout.grid, "max-h-[42vh] overflow-hidden")}>
                      {recommendations.map((rec) => (
                        <PoolCard key={rec.pool.id} pool={rec.pool} />
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className={memberPanel.box}>
                    <h3 className={typeScale.title}>
                      We didn&apos;t find live Pools under your specs
                    </h3>
                    <p className={typeScale.meta}>
                      Nothing on Quorum right now fits every constraint you gave. We
                      saved your Wish so Retailers can see the demand.
                    </p>
                  </div>
                )}
              </>
            ) : null}
          </div>
        </section>
      ) : (
        <div className="min-h-0 flex-1 overflow-hidden opacity-90">
          <div className="h-full overflow-hidden [mask-image:linear-gradient(to_bottom,black_70%,transparent)]">
            <PoolBrowser />
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
