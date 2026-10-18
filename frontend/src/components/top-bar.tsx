"use client";

import Link from "next/link";
import { formatSimClock } from "@/lib/pools";
import { buttonVariants } from "@/components/ui/button";
import { layout, typeScale } from "@/design/tokens";
import { useAccount } from "@/components/account-provider";
import { AccountSwitcher } from "@/components/account-switcher";
import { DemoDrawer } from "@/components/demo-drawer";
import { NotificationBell } from "@/components/notification-bell";

export function TopBar() {
  const { clock, user } = useAccount();

  return (
    <header className={layout.topBar}>
      <div className={layout.topBarInner}>
        <Link href="/" className={typeScale.wordmark}>
          Quorum
        </Link>
        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <div className="hidden text-right sm:block">
            <p className={typeScale.eyebrow}>Sim Clock</p>
            <p className={typeScale.meta} aria-live="polite">
              {clock ? formatSimClock(clock) : "—"}
            </p>
          </div>
          {user?.role === "retailer" ? (
            <>
              <Link href="/retailer" className={buttonVariants({ variant: "ghost" })}>
                Dashboard
              </Link>
              <Link href="/retailer/products/new" className={buttonVariants({ variant: "ghost" })}>
                New product
              </Link>
            </>
          ) : (
            <Link href="/orders" className={buttonVariants({ variant: "ghost" })}>
              My Orders
            </Link>
          )}
          <NotificationBell />
          <DemoDrawer />
          <AccountSwitcher />
        </div>
      </div>
    </header>
  );
}
