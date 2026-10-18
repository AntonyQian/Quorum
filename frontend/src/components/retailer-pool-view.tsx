"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import { TierProgressBar } from "@/components/tier-progress-bar";
import { useAccount } from "@/components/account-provider";
import { POLL_INTERVAL_MS, memberCountLabel, memberStatusLabel, textLink, typeScale } from "@/design/tokens";
import { api } from "@/lib/api";
import { formatCents } from "@/lib/money";
import { formatSimClock } from "@/lib/pools";
import type { RetailerPool } from "@/lib/types";

export function RetailerPoolView({ poolId }: { poolId: number }) {
  const { userId, ready, dataVersion } = useAccount();
  const [pool, setPool] = useState<RetailerPool | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || !Number.isFinite(poolId)) return;
    let cancelled = false;

    async function load() {
      try {
        const next = await api.getRetailerPool(poolId);
        if (!cancelled) {
          setPool(next);
          setError(null);
        }
      } catch {
        if (!cancelled) setError("This Pool is not available.");
      }
    }

    void load();
    const timer = window.setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [poolId, userId, ready, dataVersion]);

  if (error && !pool) return <p className="text-destructive">{error}</p>;
  if (!pool) return null;

  return (
    <section className="flex flex-col gap-5">
      <Link href="/retailer" className={textLink}>← Dashboard</Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className={typeScale.display}>{pool.product.name}</h1>
        <StatusBadge status={pool.status} />
      </div>
      <p className={typeScale.meta}>
        {memberCountLabel(pool.participants)} · current price {formatCents(pool.current_price_cents)} ·
        Revenue {formatCents(pool.revenue_cents)}
      </p>
      <TierProgressBar pool={pool} />

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className={typeScale.eyebrow}>
            <tr>
              <th className="py-2 pr-3">Member</th>
              <th className="py-2 pr-3">Status</th>
              <th className="py-2 pr-3">Charged</th>
              <th className="py-2 pr-3">Refunded</th>
              <th className="py-2">Joined</th>
            </tr>
          </thead>
          <tbody>
            {pool.members.map((member, index) => (
              <tr key={index} className="border-t">
                <td className="py-2 pr-3">{member.name}</td>
                <td className="py-2 pr-3">{memberStatusLabel[member.status]}</td>
                <td className="py-2 pr-3 tabular-nums">{formatCents(member.charged_cents)}</td>
                <td className="py-2 pr-3 tabular-nums">{formatCents(member.refunded_cents)}</td>
                <td className="py-2">{formatSimClock(member.joined_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {pool.members.length === 0 ? <p className={typeScale.meta}>No Members yet.</p> : null}
      </div>
    </section>
  );
}
