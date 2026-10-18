"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { DiscountOffer } from "@/components/discount-offer";
import { JoinPanel } from "@/components/join-panel";
import { StatusBadge } from "@/components/status-badge";
import { useAccount } from "@/components/account-provider";
import {
  MOMENT_MS,
  POLL_INTERVAL_MS,
  momentRest,
  poolMoment,
  skeleton,
  textLink,
  typeScale,
} from "@/design/tokens";
import { ApiError, api } from "@/lib/api";
import { formatCents } from "@/lib/money";
import { formatTimeLeft } from "@/lib/pools";
import type { PoolDetail, PoolStatus } from "@/lib/types";

function timeLabel(seconds: number): string {
  const formatted = formatTimeLeft(seconds);
  return formatted === "Ended" ? formatted : `${formatted} left`;
}

export function PoolDetailView({ poolId }: { poolId: number }) {
  const { userId, ready, dataVersion } = useAccount();
  const [pool, setPool] = useState<PoolDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [momentStatus, setMomentStatus] = useState<PoolStatus | null>(null);
  const lastStatus = useRef<PoolStatus | null>(null);

  useEffect(() => {
    if (!Number.isFinite(poolId) || !ready) return;
    let cancelled = false;
    let loaded = false;

    async function load() {
      try {
        const next = await api.getPool(poolId);
        if (cancelled) return;
        loaded = true;
        setPool(next);
        setError(null);
      } catch (err) {
        if (cancelled || loaded) return;
        setError(
          err instanceof ApiError && err.code === "not_found"
            ? "This Pool is not available."
            : "Couldn't load this Pool.",
        );
      }
    }

    void load();
    const timer = window.setInterval(() => {
      void load();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [poolId, userId, ready, dataVersion]);

  // Play the moment when a Pool this page already showed changes to locked or completed.
  const status = pool?.status ?? null;
  useEffect(() => {
    const previous = lastStatus.current;
    lastStatus.current = status;
    if (!previous || !status || previous === status || !poolMoment[status]) return;
    setMomentStatus(status);
    const timer = window.setTimeout(() => setMomentStatus(null), MOMENT_MS);
    return () => window.clearTimeout(timer);
  }, [status]);

  if (!Number.isFinite(poolId)) {
    return <p className={typeScale.meta}>This Pool is not available.</p>;
  }

  if (error && !pool) {
    return (
      <div className="flex flex-col gap-3">
        <Link href="/" className={textLink}>
          All Pools
        </Link>
        <p className={typeScale.meta}>{error}</p>
      </div>
    );
  }

  if (!pool) {
    return <div className={`${skeleton} h-96`} />;
  }

  const ended = formatTimeLeft(pool.time_left_seconds) === "Ended";
  const settled = pool.status === "completed" || pool.status === "failed";
  const activeMoment = momentStatus ? poolMoment[momentStatus] : undefined;

  return (
    <article className="flex flex-col gap-6">
      <Link href="/" className={textLink}>
        All Pools
      </Link>
      <div className="grid gap-6 lg:grid-cols-2 lg:items-start lg:gap-12">
        <div className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-muted lg:sticky lg:top-16 lg:aspect-square">
          <Image
            src={pool.product.image_url}
            alt={pool.product.name}
            fill
            priority
            sizes="(min-width: 1024px) 560px, 100vw"
            className="object-cover"
          />
        </div>
        <div className="flex flex-col gap-6">
          <header className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <StatusBadge status={pool.status} />
              <p className={typeScale.meta}>{pool.product.retailer_name}</p>
            </div>
            <h1 className={typeScale.display}>{pool.product.name}</h1>
            <p className="text-base leading-relaxed text-muted-foreground">
              {pool.product.description}
            </p>
            <p className={typeScale.meta}>{pool.product.dimensions}</p>
          </header>
          {activeMoment ? (
            <p key={momentStatus} role="status" className={activeMoment.banner}>
              {activeMoment.text}
            </p>
          ) : null}
          <div className="flex flex-col gap-4 border-t border-border pt-6">
            <div className={activeMoment?.ring ?? momentRest}>
              <DiscountOffer pool={pool} />
            </div>
            {pool.final_price_cents != null ? (
              <p className={typeScale.meta}>
                Final price {formatCents(pool.final_price_cents)}
              </p>
            ) : null}
            {settled ? null : (
              <p className={typeScale.meta}>
                <span className="font-medium text-foreground tabular-nums">
                  {timeLabel(pool.time_left_seconds)}
                </span>
                {ended ? "" : " until the Deadline"}
              </p>
            )}
          </div>
          <JoinPanel pool={pool} onChange={setPool} />
        </div>
      </div>
    </article>
  );
}
