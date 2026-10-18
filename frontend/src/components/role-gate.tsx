"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAccount } from "@/components/account-provider";
import type { UserRole } from "@/lib/types";

export function homeFor(role: UserRole): string {
  return role === "retailer" ? "/retailer" : "/";
}

/** Renders its children only for `role`; any other signed-in account is sent to its own home. */
export function RoleGate({ role, children }: { role: UserRole; children: ReactNode }) {
  const { user } = useAccount();
  const router = useRouter();
  const wrong = user != null && user.role !== role;

  useEffect(() => {
    if (wrong && user) router.replace(homeFor(user.role));
  }, [wrong, user, router]);

  if (!user || wrong) return null;
  return <>{children}</>;
}
