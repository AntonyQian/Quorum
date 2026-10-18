"use client";

import { useLayoutEffect, useRef } from "react";
import Image from "next/image";
import { Bell } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { chip, layout, typeScale } from "@/design/tokens";
import { formatCents } from "@/lib/money";
import type { Notification, RetailerProduct } from "@/lib/types";
import { cn } from "cn";

const WALNUT_IMAGE =
  "https://images.unsplash.com/photo-1615066390971-03e4e1c36ddf?auto=format&fit=crop&w=1200&q=80";

type RetailerSceneProps = {
  demandHits: number;
  threshold: number;
  launchGlow: boolean;
  zoomNotifications: boolean;
  unread: number;
  notificationsOpen: boolean;
  notifications: Notification[];
  onBellMeasure: (center: { x: number; y: number }) => void;
};

function ProductImage({ name }: { name: string }) {
  return (
    <div className="relative size-20 shrink-0 overflow-hidden rounded-lg bg-muted">
      <Image src={WALNUT_IMAGE} alt={name} fill sizes="80px" className="object-cover" />
    </div>
  );
}

export function VideoDemoRetailerScene({
  demandHits,
  threshold,
  launchGlow,
  zoomNotifications,
  unread,
  notificationsOpen,
  notifications,
  onBellMeasure,
}: RetailerSceneProps) {
  const bellRef = useRef<HTMLButtonElement>(null);
  const reached = demandHits >= threshold;
  const percent = Math.min(100, (demandHits / threshold) * 100);

  useLayoutEffect(() => {
    const node = bellRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    onBellMeasure({
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2,
    });
  }, [onBellMeasure, zoomNotifications, unread, notificationsOpen, demandHits]);

  const product: Pick<RetailerProduct, "name" | "list_price_cents" | "floor_price_cents"> = {
    name: "Walnut Dining Table",
    list_price_cents: 90000,
    floor_price_cents: 60000,
  };

  return (
    <div
      className={cn(
        "relative h-full w-full origin-top-right transition-transform duration-[1.8s] ease-[cubic-bezier(0.22,1,0.36,1)]",
        zoomNotifications ? "scale-[1.85] -translate-x-[18%] translate-y-[6%]" : "scale-100",
      )}
    >
      <header className="border-b bg-background/90 px-3 backdrop-blur-md">
        <div className="mx-auto flex h-11 w-full max-w-6xl items-center gap-2">
          <span className={typeScale.wordmark}>Quorum</span>
          <div className="ml-auto flex items-center gap-2">
            <span className={cn(buttonVariants({ variant: "outline", size: "sm" }), "pointer-events-none")}>
              Oak &amp; Co.
            </span>
            <div className="relative">
              <button
                type="button"
                ref={bellRef}
                aria-label={
                  unread > 0 ? `Notifications, ${unread} unread` : "Notifications"
                }
                className={cn(
                  buttonVariants({ variant: "outline", size: "icon" }),
                  "relative transition-shadow duration-700",
                  zoomNotifications && unread > 0
                    ? "shadow-[0_0_0_3px_color-mix(in_oklab,var(--primary)_35%,transparent)] ring-2 ring-primary/40"
                    : undefined,
                )}
              >
                <Bell />
                {unread > 0 ? (
                  <Badge
                    className={cn(
                      "absolute -top-1 -right-1 h-4 min-w-4 px-1 transition-transform duration-500",
                      unread > 0 && zoomNotifications ? "scale-110 animate-pulse" : undefined,
                    )}
                  >
                    {unread}
                  </Badge>
                ) : null}
              </button>

              {notificationsOpen ? (
                <div
                  className="absolute top-[calc(100%+0.5rem)] right-0 z-[120] w-80 animate-in fade-in slide-in-from-top-2 rounded-md border bg-popover p-1 text-popover-foreground shadow-md duration-300"
                  style={{
                    transform: zoomNotifications ? "scale(0.54)" : undefined,
                    transformOrigin: "top right",
                  }}
                >
                  <p className="px-2 py-1.5 text-sm font-medium">Notifications</p>
                  <div className="flex max-h-64 flex-col gap-0.5 overflow-hidden">
                    {notifications.map((note) => (
                      <div
                        key={note.id}
                        className={cn(
                          "rounded-sm px-2 py-2 text-sm transition-colors",
                          !note.read && "bg-accent/60",
                        )}
                      >
                        <p className={cn(!note.read && "font-semibold")}>{note.title}</p>
                        <p className="text-xs text-muted-foreground">{note.body}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </header>

      <div className={cn(layout.page, "max-w-6xl gap-5 py-5")}>
        <div>
          <h1 className={typeScale.display}>Dashboard</h1>
          <p className={typeScale.meta}>Your Pools and Hidden Listings.</p>
        </div>

        <div className={layout.cluster} role="tablist">
          <span className={cn(chip.base, chip.idle)}>Live Pools (1)</span>
          <span className={cn(chip.base, chip.selected)}>Hidden Listings (1)</span>
        </div>

        <Card className={reached ? "ring-2 ring-primary/30 transition-shadow duration-700" : undefined}>
          <CardContent className="flex items-center gap-3">
            <ProductImage name={product.name} />
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <p className={`${typeScale.title} truncate`}>{product.name}</p>
              <div
                className="h-2 overflow-hidden rounded-full bg-muted"
                role="progressbar"
                aria-valuenow={demandHits}
                aria-valuemax={threshold}
              >
                <div
                  className="h-full rounded-full bg-primary transition-[width] duration-[2.8s] ease-out"
                  style={{ width: `${percent}%` }}
                />
              </div>
              <p className={typeScale.meta}>
                <span className="tabular-nums transition-all duration-300">{demandHits}</span>
                {` / ${threshold}`} Demand Hits · 4 in the last 7 days
              </p>
              <p className={typeScale.meta}>
                List {formatCents(product.list_price_cents)} · Floor{" "}
                {formatCents(product.floor_price_cents)}
              </p>
            </div>
            <Button
              variant={reached ? "default" : "outline"}
              className={cn(
                "shrink-0 transition-all duration-700",
                launchGlow &&
                  reached &&
                  "animate-[pulse_2s_ease-in-out_infinite] shadow-[0_0_22px_color-mix(in_oklab,var(--primary)_55%,transparent)]",
              )}
            >
              Launch
            </Button>
          </CardContent>
        </Card>
      </div>

    </div>
  );
}
