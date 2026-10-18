"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { X } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { useAccount } from "@/components/account-provider";
import { demo, memberCountLabel, memberPanel, poolStatus, typeScale } from "@/design/tokens";
import { ApiError, api } from "@/lib/api";
import { friendlyError } from "@/lib/errors";
import { formatSimClock } from "@/lib/pools";
import type { PoolSummary, RetailerProduct } from "@/lib/types";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={demo.section}>
      <h3 className={typeScale.eyebrow}>{title}</h3>
      {children}
    </section>
  );
}

function poolIdFromPath(pathname: string): number | null {
  const match = /^\/pools\/(\d+)/.exec(pathname);
  return match ? Number(match[1]) : null;
}

/** The presenter's controls: Sim Clock, simulated joins and demand, and reset (SPEC §8 demo endpoints). */
export function DemoDrawer() {
  const { clock, user, dataVersion, refresh } = useAccount();
  const [open, setOpen] = useState(false);
  const [pools, setPools] = useState<PoolSummary[]>([]);
  const [hidden, setHidden] = useState<RetailerProduct[]>([]);
  const [poolId, setPoolId] = useState<number | null>(null);
  const [joinCount, setJoinCount] = useState(8);
  const [leaveCount, setLeaveCount] = useState(1);
  const [declining, setDeclining] = useState(false);
  const [productId, setProductId] = useState<number | null>(null);
  const [demandCount, setDemandCount] = useState(1);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ text: string; error: boolean } | null>(null);
  const isRetailer = user?.role === "retailer";

  // Load the pickers when the drawer opens and after each action, preferring the Pool on screen.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    // Read at open time; usePathname here would keep the top bar out of the prerendered shell.
    const onScreen = poolIdFromPath(window.location.pathname);
    api
      .listPools({ status: "open,locked" })
      .then((live) => {
        if (cancelled) return;
        setPools(live);
        setPoolId((current) => {
          if (onScreen != null && live.some((pool) => pool.id === onScreen)) return onScreen;
          if (current != null && live.some((pool) => pool.id === current)) return current;
          return live[0]?.id ?? null;
        });
      })
      .catch(() => {
        if (!cancelled) setPools([]);
      });
    if (isRetailer) {
      api
        .listRetailerProducts()
        .then((products) => {
          if (cancelled) return;
          const listings = products.filter((product) => product.visibility === "hidden");
          setHidden(listings);
          setProductId((current) => current ?? listings[0]?.id ?? null);
        })
        .catch(() => {
          if (!cancelled) setHidden([]);
        });
    }
    return () => {
      cancelled = true;
    };
  }, [open, isRetailer, dataVersion]);

  async function act(run: () => Promise<string>) {
    setBusy(true);
    setStatus(null);
    try {
      const text = await run();
      await refresh();
      setStatus({ text, error: false });
    } catch (err) {
      // Demo errors go to the presenter, so the server's own message is the useful one.
      setStatus({ text: err instanceof ApiError ? err.message : friendlyError(err), error: true });
    } finally {
      setBusy(false);
    }
  }

  const selectedPool = pools.find((pool) => pool.id === poolId) ?? null;

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger className={buttonVariants({ variant: "outline" })}>Demo</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className={demo.backdrop} />
        <Dialog.Popup className={demo.panel}>
          <div className="flex items-center justify-between">
            <Dialog.Title className={typeScale.title}>Demo</Dialog.Title>
            <Dialog.Close
              aria-label="Close"
              className={buttonVariants({ variant: "ghost", size: "icon" })}
            >
              <X />
            </Dialog.Close>
          </div>

          <Section title="Sim Clock">
            <p className={typeScale.meta}>{clock ? formatSimClock(clock) : "—"}</p>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                disabled={busy}
                onClick={() =>
                  void act(async () => {
                    const { now } = await api.advanceClock({ days: 1 });
                    return `Sim Clock is now ${formatSimClock(now)}.`;
                  })
                }
              >
                +1 day
              </Button>
              <Button
                variant="outline"
                disabled={busy}
                onClick={() =>
                  void act(async () => {
                    const { now } = await api.advanceClock({ days: 7 });
                    return `Sim Clock is now ${formatSimClock(now)}.`;
                  })
                }
              >
                +7 days
              </Button>
              <Button
                variant="outline"
                disabled={busy || poolId == null}
                onClick={() =>
                  void act(async () => {
                    const { now } = await api.advanceClock({ to_deadline_of_pool: poolId! });
                    return `Jumped to the Deadline: ${formatSimClock(now)}.`;
                  })
                }
              >
                Jump to Deadline
              </Button>
            </div>
          </Section>

          <Section title="Pool">
            <label className={demo.field}>
              <span className={typeScale.meta}>Pool for joins and the Deadline jump</span>
              <select
                className={demo.input}
                value={poolId ?? ""}
                onChange={(event) => setPoolId(Number(event.target.value))}
                disabled={pools.length === 0}
              >
                {pools.length === 0 ? <option value="">No live Pools</option> : null}
                {pools.map((pool) => (
                  <option key={pool.id} value={pool.id}>
                    #{pool.id} {pool.product.name} · {memberCountLabel(pool.participants)}, {poolStatus[pool.status].label}
                  </option>
                ))}
              </select>
            </label>
          </Section>

          <Section title="Simulate joins">
            <div className="flex flex-wrap items-end gap-2">
              <label className={demo.field}>
                <span className={typeScale.meta}>Simulated Shoppers</span>
                <input
                  type="number"
                  min={1}
                  max={200}
                  className={`${demo.input} w-24`}
                  value={joinCount}
                  onChange={(event) => setJoinCount(Number(event.target.value))}
                />
              </label>
              <Button
                disabled={busy || poolId == null || joinCount < 1 || joinCount > 200}
                onClick={() =>
                  void act(async () => {
                    const pool = await api.simulateJoins(poolId!, {
                      count: joinCount,
                      include_declining_card: declining,
                    });
                    return `${selectedPool?.product.name ?? "The Pool"} now has ${memberCountLabel(pool.participants)} and is ${poolStatus[pool.status].label}.`;
                  })
                }
              >
                Simulate joins
              </Button>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={declining}
                onChange={(event) => setDeclining(event.target.checked)}
              />
              Include a declining card
            </label>
          </Section>

          <Section title="Simulate leaves">
            <div className="flex flex-wrap items-end gap-2">
              <label className={demo.field}>
                <span className={typeScale.meta}>Members who leave</span>
                <input
                  type="number"
                  min={1}
                  max={200}
                  className={`${demo.input} w-24`}
                  value={leaveCount}
                  onChange={(event) => setLeaveCount(Number(event.target.value))}
                />
              </label>
              <Button
                variant="outline"
                disabled={busy || poolId == null || leaveCount < 1 || leaveCount > 200}
                onClick={() =>
                  void act(async () => {
                    const pool = await api.simulateLeaves(poolId!, leaveCount);
                    return `${selectedPool?.product.name ?? "The Pool"} now has ${memberCountLabel(pool.participants)}.`;
                  })
                }
              >
                Simulate leaves
              </Button>
            </div>
          </Section>

          <Section title="Simulate demand">
            <div className="flex flex-wrap items-end gap-2">
              <label className={demo.field}>
                <span className={typeScale.meta}>Hidden Listing</span>
                {hidden.length > 0 ? (
                  <select
                    className={demo.input}
                    value={productId ?? ""}
                    onChange={(event) => setProductId(Number(event.target.value))}
                  >
                    {hidden.map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.name}
                        {product.demand
                          ? ` (${product.demand.total_hits}/${product.demand.threshold ?? "—"})`
                          : ""}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    min={1}
                    placeholder="Product id"
                    className={`${demo.input} w-28`}
                    value={productId ?? ""}
                    onChange={(event) =>
                      setProductId(event.target.value ? Number(event.target.value) : null)
                    }
                  />
                )}
              </label>
              <label className={demo.field}>
                <span className={typeScale.meta}>Wishes</span>
                <input
                  type="number"
                  min={1}
                  max={200}
                  className={`${demo.input} w-20`}
                  value={demandCount}
                  onChange={(event) => setDemandCount(Number(event.target.value))}
                />
              </label>
              <Button
                disabled={busy || productId == null || demandCount < 1 || demandCount > 200}
                onClick={() =>
                  void act(async () => {
                    const { total_hits } = await api.simulateDemand(productId!, demandCount);
                    return `That Hidden Listing now has ${total_hits} Demand Hits.`;
                  })
                }
              >
                Simulate demand
              </Button>
              <Button
                variant="outline"
                disabled={busy || productId == null || demandCount < 1 || demandCount > 200}
                onClick={() =>
                  void act(async () => {
                    const { total_hits } = await api.removeDemand(productId!, demandCount);
                    return `That Hidden Listing now has ${total_hits} Demand Hits.`;
                  })
                }
              >
                Remove demand
              </Button>
            </div>
            {!isRetailer ? (
              <p className={typeScale.meta}>
                Switch to a Retailer to pick from their Hidden Listings.
              </p>
            ) : null}
          </Section>

          <Section title="Reset">
            <Button
              variant="destructive"
              disabled={busy}
              onClick={() =>
                void act(async () => {
                  await api.resetDemo();
                  return "The demo data was reset.";
                })
              }
            >
              Reset demo
            </Button>
          </Section>

          {status ? (
            <p
              role={status.error ? "alert" : "status"}
              className={status.error ? memberPanel.error : memberPanel.line}
            >
              {status.text}
            </p>
          ) : null}
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
