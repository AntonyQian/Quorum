"use client";

import { useEffect, useMemo, useState } from "react";
import { CategoryChips } from "@/components/category-chips";
import { PoolCard } from "@/components/pool-card";
import { Button } from "@/components/ui/button";
import { useAccount } from "@/components/account-provider";
import {
  categoryLabel,
  filter,
  layout,
  poolScopes,
  skeleton,
  typeScale,
} from "@/design/tokens";
import { api } from "@/lib/api";
import { filterPoolsByCategory } from "@/lib/pools";
import type { PoolStatus, PoolSummary } from "@/lib/types";
import { cn } from "cn";

type Scope = keyof typeof poolScopes;

export function PoolBrowser() {
  const { userId, dataVersion } = useAccount();
  const [pools, setPools] = useState<PoolSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scope, setScope] = useState<Scope>("live");
  const [category, setCategory] = useState<string | null>(null);
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

  const categories = useMemo(() => {
    const ids = [...new Set(scoped.map((pool) => pool.product.category))];
    return ids.map((id) => ({ id, label: categoryLabel(id) }));
  }, [scoped]);

  const visible = filterPoolsByCategory(
    scoped,
    categories.some((entry) => entry.id === category) ? category : null,
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
              onClick={() => {
                setScope(key);
                setCategory(null);
              }}
            >
              {poolScopes[key].label}
            </button>
          ))}
        </div>
        <CategoryChips
          categories={categories}
          selected={
            categories.some((entry) => entry.id === category) ? category : null
          }
          onSelect={setCategory}
        />
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
          {category ? "No Pools in this category." : "No Pools here yet."}
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
