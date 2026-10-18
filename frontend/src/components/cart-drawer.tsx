"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Dialog } from "@base-ui/react/dialog";
import { ShoppingCart, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { useAccount } from "@/components/account-provider";
import { cart, memberStatusLabel, typeScale } from "@/design/tokens";
import { api } from "@/lib/api";
import { formatCents } from "@/lib/money";
import { isActiveMember } from "@/lib/membership";
import type { PoolDetail } from "@/lib/types";
import { cn } from "cn";

async function loadCartPools(): Promise<PoolDetail[]> {
  const live = await api.listPools({ status: "open,locked" });
  const details = await Promise.all(live.map((pool) => api.getPool(pool.id)));
  return details.filter((pool) => isActiveMember(pool.my_membership));
}

export function CartDrawer() {
  const { userId, dataVersion } = useAccount();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState<PoolDetail[]>([]);
  const [count, setCount] = useState(0);

  const refresh = useCallback(async () => {
    if (!userId) {
      setItems([]);
      setCount(0);
      return;
    }
    try {
      const next = await loadCartPools();
      setItems(next);
      setCount(next.length);
    } catch {
      setItems([]);
      setCount(0);
    }
  }, [userId]);

  useEffect(() => {
    void refresh();
  }, [refresh, dataVersion]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setBusy(true);
    loadCartPools()
      .then((next) => {
        if (!cancelled) {
          setItems(next);
          setCount(next.length);
        }
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, dataVersion]);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger
        aria-label={count > 0 ? `Cart, ${count} Pools` : "Cart"}
        className={cn(buttonVariants({ variant: "outline", size: "icon" }), "relative shrink-0")}
      >
        <ShoppingCart />
        {count > 0 ? (
          <Badge className="absolute -top-1 -right-1 h-4 min-w-4 px-1 tabular-nums">{count}</Badge>
        ) : null}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className={cart.backdrop} />
        <Dialog.Popup className={cart.panel}>
          <div className={cart.header}>
            <Dialog.Title className={typeScale.title}>Your cart</Dialog.Title>
            <Dialog.Close
              aria-label="Close cart"
              className={buttonVariants({ variant: "ghost", size: "icon" })}
            >
              <X />
            </Dialog.Close>
          </div>

          <div className={cart.body}>
            <p className={typeScale.meta}>
              Pools you&apos;ve joined. You&apos;re not charged until a Pool Locks (or when you join a
              locked Pool).
            </p>

            {busy ? (
              <p className={typeScale.meta} aria-live="polite">
                Loading…
              </p>
            ) : items.length === 0 ? (
              <div className="flex flex-col gap-3 py-6">
                <p className={typeScale.meta}>Your cart is empty.</p>
                <Link href="/" className={buttonVariants({ variant: "outline" })} onClick={() => setOpen(false)}>
                  Browse Pools
                </Link>
              </div>
            ) : (
              <ul className="flex flex-col gap-3">
                {items.map((pool) => {
                  const membership = pool.my_membership!;
                  return (
                    <li key={pool.id}>
                      <Link
                        href={`/pools/${pool.id}`}
                        className={cart.item}
                        onClick={() => setOpen(false)}
                      >
                        <div className="relative size-16 shrink-0 overflow-hidden rounded-lg">
                          <Image
                            src={pool.product.image_url}
                            alt=""
                            fill
                            sizes="64px"
                            className="object-cover"
                          />
                        </div>
                        <div className="flex min-w-0 flex-1 flex-col gap-1">
                          <p className={`${typeScale.title} truncate`}>{pool.product.name}</p>
                          <p className={`${typeScale.meta} truncate`}>{pool.product.retailer_name}</p>
                          <p className="text-sm font-semibold tabular-nums text-primary">
                            {formatCents(pool.current_price_cents)}
                          </p>
                          <p className={typeScale.meta}>{memberStatusLabel[membership.status]}</p>
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}

            {items.length > 0 ? (
              <div className="mt-auto border-t border-border/40 pt-4">
                <Link
                  href="/orders"
                  className={cn(buttonVariants({ variant: "secondary" }), "w-full")}
                  onClick={() => setOpen(false)}
                >
                  View order history
                </Link>
              </div>
            ) : null}
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
