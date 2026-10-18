"use client";

import Link from "next/link";
import { layout, typeScale } from "@/design/tokens";
import { useAccount } from "@/components/account-provider";
import { AccountSwitcher } from "@/components/account-switcher";
import { AdminNavButton } from "@/components/admin-nav-button";
import { CartDrawer } from "@/components/cart-drawer";
import { NotificationBell } from "@/components/notification-bell";
import { HowItWorksButton, OnboardingModal } from "@/components/onboarding-modal";
import { RetailerPortalDrawer } from "@/components/retailer-portal-drawer";
import { homeFor } from "@/components/role-gate";

function RoleTray() {
  const { user } = useAccount();

  if (user?.role === "shopper") {
    return (
      <>
        <HowItWorksButton />
        <CartDrawer />
      </>
    );
  }

  if (user?.role === "retailer") {
    return (
      <>
        <NotificationBell />
        <RetailerPortalDrawer />
        <AdminNavButton />
      </>
    );
  }

  if (user?.role === "admin") {
    return <AdminNavButton />;
  }

  return null;
}

export function TopBar() {
  const { user } = useAccount();
  const home = user ? homeFor(user.role) : "/";

  return (
    <header className={layout.topBar}>
      <div className={layout.topBarInner}>
        <Link href={home} className={typeScale.wordmark}>
          Quorum <span className="text-green-800 font-3xl ml-[-3px]">.</span>
        </Link>
        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <AccountSwitcher />
          <div className="flex items-center gap-0.5 sm:gap-1">{RoleTray()}</div>
        </div>
      </div>
      <OnboardingModal />
    </header>
  );
}
