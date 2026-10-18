"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/status-badge";
import { useAccount } from "@/components/account-provider";
import {
  failedAmount,
  layout,
  memberPanel,
  memberStatusLabel,
  skeleton,
  textLink,
  typeScale,
} from "@/design/tokens";
import { api } from "@/lib/api";
import { friendlyError } from "@/lib/errors";
import { formatCents } from "@/lib/money";
import { totalSavingsCents } from "@/lib/orders";
import { formatSimClock } from "@/lib/pools";
import type { Order } from "@/lib/types";

function paymentLabel(payment: Order["payments"][number]): string {
  const kind = payment.kind === "charge" ? "Charge" : "Tier Refund";
  return payment.status === "failed" ? `${kind} failed` : kind;
}

export function OrdersView() {
  const { user, userId, ready, dataVersion } = useAccount();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const isRetailer = user?.role === "retailer";

  useEffect(() => {
    if (!ready || !userId || isRetailer) return;
    let cancelled = false;
    api
      .listOrders()
      .then((next) => {
        if (cancelled) return;
        setOrders(next);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(friendlyError(err));
      });
    return () => {
      cancelled = true;
    };
  }, [ready, userId, isRetailer, dataVersion, reloadKey]);

  const savings = orders ? totalSavingsCents(orders) : 0;

  return (
    <section className={layout.stack}>
      <div>
        <h1 className={typeScale.display}>My Orders</h1>
        {orders && savings > 0 ? (
          <p className={typeScale.savings}>
            You saved {formatCents(savings)} vs list price
          </p>
        ) : null}
      </div>
      {isRetailer ? (
        <p className={typeScale.meta}>My Orders is for Shoppers. Switch accounts in the top bar.</p>
      ) : error ? (
        <div className="flex flex-col items-start gap-3">
          <p className={memberPanel.error}>Couldn&apos;t load your orders. {error}</p>
          <Button variant="outline" onClick={() => setReloadKey((key) => key + 1)}>
            Retry
          </Button>
        </div>
      ) : orders == null ? (
        <div className={`${skeleton} h-40`} aria-hidden />
      ) : orders.length === 0 ? (
        <p className={typeScale.meta}>
          No orders yet. <Link href="/" className={textLink}>Browse Pools</Link>
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {orders.map((order) => (
            <li key={order.pool_id}>
              <Card>
                <CardContent className="flex flex-col gap-3 sm:flex-row">
                  <Link
                    href={`/pools/${order.pool_id}`}
                    className="relative aspect-[4/3] w-full shrink-0 overflow-hidden rounded-lg bg-muted sm:w-40"
                  >
                    <Image
                      src={order.product.image_url}
                      alt={order.product.name}
                      fill
                      sizes="(min-width: 640px) 160px, 100vw"
                      className="object-cover"
                    />
                  </Link>
                  <div className="flex min-w-0 flex-1 flex-col gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link href={`/pools/${order.pool_id}`} className={typeScale.title}>
                        {order.product.name}
                      </Link>
                      <StatusBadge status={order.pool_status} />
                    </div>
                    <p className={typeScale.meta}>
                      {order.product.retailer_name} · {memberStatusLabel[order.member_status]}
                    </p>
                    {order.payments.length > 0 ? (
                      <ul className="flex flex-col gap-1 border-t border-border pt-2 text-sm">
                        {order.payments.map((payment, index) => (
                          <li
                            key={`${payment.created_at}-${index}`}
                            className="flex items-baseline justify-between gap-3"
                          >
                            <span>
                              {paymentLabel(payment)}
                              <span className={`ml-2 ${typeScale.meta}`}>
                                {formatSimClock(payment.created_at)}
                              </span>
                            </span>
                            <span
                              className={
                                payment.status === "failed" ? failedAmount : "tabular-nums"
                              }
                            >
                              {payment.kind === "refund" ? "−" : ""}
                              {formatCents(payment.amount_cents)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className={typeScale.meta}>No charges yet.</p>
                    )}
                    <div className="flex items-baseline justify-between gap-3 border-t border-border pt-2">
                      <span className={typeScale.eyebrow}>Net paid</span>
                      <span className={typeScale.price}>{formatCents(order.net_paid_cents)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
