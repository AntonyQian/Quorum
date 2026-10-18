"use client";

import { useState, type FormEvent } from "react";
import { flushSync } from "react-dom";
import { Loader2, Search } from "lucide-react";
import { PoolBrowser } from "@/components/pool-browser";
import { PoolCard } from "@/components/pool-card";
import { Button } from "@/components/ui/button";
import { layout, memberPanel, skeleton, typeScale } from "@/design/tokens";
import { ApiError, api } from "@/lib/api";
import type { RecommendResponse } from "@/lib/types";
import { cn } from "cn";

type HomeMode = "browse" | "wish";

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
         <section
            className={cn(
               "mx-auto flex w-full max-w-xl flex-col items-center gap-5 text-center",
               mode === "browse" ? "my-[10%]" : "mt-4",
            )}
         >
            <h1 className="font-heading text-2xl font-medium tracking-tight text-balance sm:text-[1.75rem]">
               What are you looking for?
            </h1>
            <form onSubmit={submit} className="w-full">
               <div className="relative">
                  <button
                     type="submit"
                     disabled={busy || !query.trim()}
                     aria-label={busy ? "Searching" : "Search"}
                     className={cn(
                        "absolute top-1/2 right-1.5 flex size-9 -translate-y-1/2 items-center justify-center rounded-full",
                        "bg-primary text-primary-foreground transition-opacity",
                        "disabled:cursor-not-allowed disabled:opacity-40",
                        "outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1",
                     )}
                  >
                     {busy ? (
                        <Loader2 className="size-4 animate-spin" aria-hidden />
                     ) : (
                        <Search className="size-4" aria-hidden />
                     )}
                  </button>
                  <input
                     value={query}
                     onChange={(event) => setQuery(event.target.value)}
                     placeholder="A walnut dining table for six, under $1,200"
                     aria-label="Describe what you want"
                     className="h-12 w-full rounded-full border border-input bg-background py-2 pr-12 pl-4 text-sm outline-none focus-visible:border-ring focus-visible:ring-0"
                  />
               </div>
            </form>

            {error ? (
               <p
                  className={cn(memberPanel.error, "w-full max-w-xl text-left")}
                  role="alert"
               >
                  {error}
               </p>
            ) : null}
         </section>

         {mode === "wish" ? (
            <section className="flex flex-col gap-4">
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
                        ) : null}
                     </div>
                     {!busy && result ? (
                        <Button
                           type="button"
                           variant="outline"
                           size="sm"
                           onClick={returnToBrowse}
                        >
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
                              <h3 className={typeScale.title}>
                                 Matches for your Wish
                              </h3>
                              <div className={layout.grid}>
                                 {recommendations.map((rec) => (
                                    <PoolCard
                                       key={rec.pool.id}
                                       pool={rec.pool}
                                    />
                                 ))}
                              </div>
                           </div>
                        ) : (
                           <div className="flex flex-col gap-2">
                              <h3 className={typeScale.title}>
                                 We didn&apos;t find live Pools for this search
                              </h3>
                              <p className={typeScale.meta}>
                                 Nothing on Quorum right now fits every
                                 constraint you gave. We saved your Wish so
                                 Retailers can see the demand.
                              </p>
                           </div>
                        )}

                        {hasSuggestions ? (
                           <div className="flex flex-col gap-3 border-t border-border pt-6">
                              <h3 className={typeScale.title}>
                                 You might also like
                              </h3>
                              <p className={typeScale.meta}>
                                 {hasRecs
                                    ? "These are close, but they miss part of what you asked for."
                                    : "These Pools are nearby — they may be over budget or a different fit."}
                              </p>
                              <div className={layout.grid}>
                                 {suggestions.map((rec) => (
                                    <PoolCard
                                       key={rec.pool.id}
                                       pool={rec.pool}
                                    />
                                 ))}
                              </div>
                           </div>
                        ) : null}

                        {!hasRecs && !hasSuggestions ? (
                           <p className={typeScale.meta}>
                              Try broadening your budget or category, or check
                              back when new Pools open.
                           </p>
                        ) : null}
                     </>
                  ) : null}
               </div>
            </section>
         ) : null}

         {mode === "browse" ? <PoolBrowser /> : null}
      </div>
   );
}
