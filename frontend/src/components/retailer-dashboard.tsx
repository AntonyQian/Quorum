"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Dialog } from "@base-ui/react/dialog";
import { Trash2 } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PoolFields } from "@/components/pool-fields";
import { StatusBadge } from "@/components/status-badge";
import { useAccount } from "@/components/account-provider";
import {
  POLL_INTERVAL_MS,
  chip,
  demo,
  layout,
  memberCountLabel,
  memberPanel,
  typeScale,
} from "@/design/tokens";
import { ApiError, api } from "@/lib/api";
import { formatCents } from "@/lib/money";
import { buildPoolCreate, emptyPoolForm, type PoolFormState } from "@/lib/pool-form";
import { formatTimeLeft } from "@/lib/pools";
import type { RetailerProduct } from "@/lib/types";
import { cn } from "cn";

type Tab = "live" | "hidden";

function ProductImage({ product }: { product: RetailerProduct }) {
  return (
    <div className="relative size-20 shrink-0 overflow-hidden rounded-lg bg-muted">
      <Image src={product.image_url} alt={product.name} fill sizes="80px" className="object-cover" />
    </div>
  );
}

function LaunchDialog({
  product,
  onClose,
  onLaunched,
}: {
  product: RetailerProduct;
  onClose: () => void;
  onLaunched: () => void;
}) {
  const [form, setForm] = useState<PoolFormState>(emptyPoolForm);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function launch() {
    const built = buildPoolCreate(form, {
      listCents: product.list_price_cents,
      floorCents: product.floor_price_cents,
    });
    if ("error" in built) return setError(built.error);
    setBusy(true);
    setError(null);
    try {
      await api.launchProduct(product.id, built.pool);
      onLaunched();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't launch this Pool.");
      setBusy(false);
    }
  }

  return (
    <Dialog.Root open onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Backdrop className={demo.backdrop} />
        <Dialog.Popup className="fixed top-1/2 left-1/2 z-50 flex max-h-[90vh] w-[calc(100%-1.5rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col gap-4 overflow-y-auto rounded-xl border bg-background p-4 shadow-xl outline-none">
          <Dialog.Title className={typeScale.title}>Launch {product.name}</Dialog.Title>
          <p className={typeScale.meta}>
            List Price {formatCents(product.list_price_cents)} · Floor Price {formatCents(product.floor_price_cents)}
          </p>
          <PoolFields value={form} onChange={setForm} listCents={product.list_price_cents} />
          {error ? <p className={memberPanel.error} role="alert">{error}</p> : null}
          <div className="flex gap-2">
            <Button disabled={busy} onClick={() => void launch()}>
              {busy ? "Launching..." : "Launch Pool"}
            </Button>
            <Button variant="outline" onClick={onClose}>Cancel</Button>
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function RetailerDashboard() {
  const { userId, ready, dataVersion, refresh } = useAccount();
  const [products, setProducts] = useState<RetailerProduct[] | null>(null);
  const [revenue, setRevenue] = useState<Record<number, number>>({});
  const [error, setError] = useState<string | null>(null);
  // A demand alert links here as /retailer?product=ID: open Hidden Listings and mark that one.
  // The dashboard only mounts on the client (RoleGate waits for the account), so reading the URL is safe.
  const [focus] = useState<number | null>(
    () => Number(new URLSearchParams(window.location.search).get("product")) || null,
  );
  const [tab, setTab] = useState<Tab>(focus ? "hidden" : "live");
  const [launching, setLaunching] = useState<RetailerProduct | null>(null);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;

    async function load() {
      try {
        const next = await api.listRetailerProducts();
        if (cancelled) return;
        setProducts(next);
        setError(null);
        const pools = next.flatMap((product) => (product.pool ? [product.pool.id] : []));
        const entries = await Promise.all(
          pools.map(async (id) => [id, (await api.getRetailerPool(id)).revenue_cents] as const),
        );
        if (!cancelled) setRevenue(Object.fromEntries(entries));
      } catch {
        if (!cancelled) setError("Couldn't load your products.");
      }
    }

    void load();
    const timer = window.setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [userId, ready, dataVersion]);

  async function remove(product: RetailerProduct) {
    if (!window.confirm(`Remove ${product.name}?`)) return;
    try {
      await api.deleteRetailerProduct(product.id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't remove this product.");
    }
  }

  const live = (products ?? []).filter((p) => p.visibility === "public");
  const hidden = (products ?? []).filter((p) => p.visibility === "hidden");

  const removeButton = (product: RetailerProduct) => (
    <Button
      variant="ghost"
      size="icon"
      aria-label={`Remove ${product.name}`}
      onClick={() => void remove(product)}
    >
      <Trash2 />
    </Button>
  );

  return (
    <section className={layout.stack}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className={typeScale.display}>Dashboard</h1>
          <p className={typeScale.meta}>Your Pools and Hidden Listings.</p>
        </div>
        <Link href="/retailer/products/new" className={buttonVariants()}>
          Add product
        </Link>
      </div>

      <div className={layout.cluster} role="tablist">
        {(["live", "hidden"] as const).map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={cn(chip.base, tab === key ? chip.selected : chip.idle)}
            onClick={() => setTab(key)}
          >
            {key === "live" ? `Live Pools (${live.length})` : `Hidden Listings (${hidden.length})`}
          </button>
        ))}
      </div>

      {error ? <p className={memberPanel.error} role="alert">{error}</p> : null}

      {products == null ? null : tab === "live" ? (
        live.length === 0 ? (
          <p className={typeScale.meta}>No live products. Add one to open a Pool.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {live.map((product) => {
              const pool = product.pool;
              return (
                <Card key={product.id}>
                  <CardContent className="flex items-center gap-3">
                    <ProductImage product={product} />
                    <div className="flex min-w-0 flex-1 flex-col gap-1">
                      <p className={`${typeScale.title} truncate`}>{product.name}</p>
                      {pool ? (
                        <>
                          <div className="flex flex-wrap items-center gap-2">
                            <StatusBadge status={pool.status} />
                            <span className={typeScale.meta}>
                              {memberCountLabel(pool.participants)} · {formatCents(pool.current_price_cents)}
                              {pool.status === "open" || pool.status === "locked"
                                ? ` · ${formatTimeLeft(pool.time_left_seconds)} left`
                                : ""}
                            </span>
                          </div>
                          <p className={typeScale.meta}>
                            Revenue {formatCents(revenue[pool.id] ?? 0)}
                            {pool.next_tier ? ` · next Tier in ${pool.next_tier.needed}` : ""}
                          </p>
                        </>
                      ) : (
                        <p className={typeScale.meta}>No Pool</p>
                      )}
                    </div>
                    {pool ? (
                      <Link href={`/retailer/pools/${pool.id}`} className={buttonVariants({ variant: "outline" })}>
                        Members
                      </Link>
                    ) : null}
                    {removeButton(product)}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )
      ) : hidden.length === 0 ? (
        <p className={typeScale.meta}>No Hidden Listings.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {hidden.map((product) => {
            const demand = product.demand;
            const hits = demand?.total_hits ?? 0;
            const threshold = demand?.threshold ?? null;
            const reached = demand?.threshold_reached ?? false;
            const percent = threshold ? Math.min(100, (hits / threshold) * 100) : 0;
            return (
              <Card key={product.id} className={focus === product.id ? "ring-2 ring-primary" : undefined}>
                <CardContent className="flex items-center gap-3">
                  <ProductImage product={product} />
                  <div className="flex min-w-0 flex-1 flex-col gap-2">
                    <p className={`${typeScale.title} truncate`}>{product.name}</p>
                    <div
                      className="h-2 overflow-hidden rounded-full bg-muted"
                      role="progressbar"
                      aria-valuenow={hits}
                      aria-valuemax={threshold ?? hits}
                      aria-label="Demand toward the threshold"
                    >
                      <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
                    </div>
                    <p className={typeScale.meta}>
                      {hits}
                      {threshold ? ` / ${threshold}` : ""} Demand Hits · {demand?.last_7_days ?? 0} in the last 7 days
                    </p>
                  </div>
                  <Button
                    className={reached ? "shadow-[0_0_16px_var(--primary)]" : undefined}
                    variant={reached ? "default" : "outline"}
                    onClick={() => setLaunching(product)}
                  >
                    Launch
                  </Button>
                  {removeButton(product)}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {launching ? (
        <LaunchDialog
          product={launching}
          onClose={() => setLaunching(null)}
          onLaunched={() => {
            setLaunching(null);
            setTab("live");
            void refresh();
          }}
        />
      ) : null}
    </section>
  );
}
