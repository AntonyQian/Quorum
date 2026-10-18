"use client";

import Link from "next/link";
import { Shield } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "cn";

export function AdminNavButton() {
  return (
    <Link
      href="/admin"
      aria-label="Admin"
      className={cn(buttonVariants({ variant: "outline", size: "icon" }), "shrink-0")}
    >
      <Shield aria-hidden />
    </Link>
  );
}
