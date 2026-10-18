"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAccount } from "@/components/account-provider";
import type { UserRole } from "@/lib/types";

export function homeFor(role: UserRole): string {
  if (role === "retailer") return "/retailer";
  if (role === "admin") return "/admin";
  return "/";
}

/** Renders its children only for allowed roles; others are sent to their home. */
export function RoleGate({
  role,
  allow,
  children,
}: {
  role?: UserRole;
  allow?: UserRole[];
  children: ReactNode;
}) {
  const allowed = allow ?? (role ? [role] : []);
  const { user } = useAccount();
  const router = useRouter();
  const wrong = user != null && !allowed.includes(user.role);

  useEffect(() => {
    if (wrong && user) router.replace(homeFor(user.role));
  }, [wrong, user, router]);

  if (!user || wrong || allowed.length === 0) return null;
  return <>{children}</>;
}
