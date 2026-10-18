"use client";

import { useEffect, useMemo, useState } from "react";
import { PoolCard } from "@/components/pool-card";
import { Button } from "@/components/ui/button";
import { useAccount } from "@/components/account-provider";
import {
  filter,
  layout,
  poolBrowseCategoryOptions,
  poolScopes,
  skeleton,
  typeScale,
} from "@/design/tokens";
import { api } from "@/lib/api";
import { filterPoolsByBrowseCategory } from "@/lib/pools";
import type { PoolStatus, PoolSummary } from "@/lib/types";
import { cn } from "cn";

type Scope = keyof typeof poolScopes;

export function PoolBrowser() {
  const { userId, dataVersion } = useAccount();
  const [pools, setPools] = useState<PoolSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scope, setScope] = useState<Scope>("live");
  const [browseCategory, setBrowseCategory] = useState("all");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    api
      .listPools({ status: "open,locked,completed,failed" })
      .then((next) => {
        if (!cancelled) {
          setPools(next);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load Pools.");
      });

    return () => {
      cancelled = true;
    };
  }, [userId, dataVersion, reloadKey]);

  const scoped = useMemo(() => {
    const allowed = new Set<PoolStatus>(poolScopes[scope].statuses);
    return (pools ?? []).filter((pool) => allowed.has(pool.status));
  }, [pools, scope]);

  const visible = useMemo(
    () => filterPoolsByBrowseCategory(scoped, browseCategory),
    [scoped, browseCategory],
  );

  return (
    <section className={layout.stack}>
      <div className="flex flex-col gap-4">
        <div>
          <h2 className={typeScale.display}>Pools</h2>
          <p className={typeScale.meta}>
            The price drops when more Members join.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className={filter.segmented} role="group" aria-label="Pool status">
            {(Object.keys(poolScopes) as Scope[]).map((key) => (
              <button
                key={key}
                type="button"
                className={cn(
                  filter.segment,
                  scope === key ? filter.segmentSelected : filter.segmentIdle,
                )}
                aria-pressed={scope === key}
                onClick={() => setScope(key)}
              >
                {poolScopes[key].label}
              </button>
            ))}
          </div>
          <select
            value={browseCategory}
            onChange={(event) => setBrowseCategory(event.target.value)}
            aria-label="Category"
            className={filter.select}
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")`,
            }}
          >
            {poolBrowseCategoryOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error ? (
        <div className="flex flex-col items-start gap-3">
          <p className="text-destructive">{error}</p>
          <Button
            variant="outline"
            onClick={() => {
              setError(null);
              setReloadKey((key) => key + 1);
            }}
          >
            Retry
          </Button>
        </div>
      ) : pools == null ? (
        <div className={layout.grid} aria-hidden>
          <div className={`${skeleton} h-80`} />
          <div className={`${skeleton} h-80`} />
          <div className={`${skeleton} h-80`} />
        </div>
      ) : visible.length === 0 ? (
        <p className={typeScale.meta}>
          {browseCategory !== "all"
            ? "No Pools in this category."
            : "No Pools here yet."}
        </p>
      ) : (
        <div className={layout.grid}>
          {visible.map((pool) => (
            <PoolCard key={pool.id} pool={pool} />
          ))}
        </div>
      )}
    </section>
  );
}
