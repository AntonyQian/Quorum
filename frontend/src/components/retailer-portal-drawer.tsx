"use client";

import Link from "next/link";
import { Dialog } from "@base-ui/react/dialog";
import { LayoutGrid, PackagePlus, X } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cart, typeScale } from "@/design/tokens";
import { cn } from "cn";

const links = [
  { href: "/retailer", label: "Dashboard", icon: LayoutGrid, description: "Pools and hidden listings" },
  {
    href: "/retailer/products/new",
    label: "New product",
    icon: PackagePlus,
    description: "List a product or hidden listing",
  },
] as const;

export function RetailerPortalDrawer() {
  return (
    <Dialog.Root>
      <Dialog.Trigger
        aria-label="Retailer portal"
        className={cn(buttonVariants({ variant: "outline", size: "icon" }), "relative shrink-0")}
      >
        <LayoutGrid />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className={cart.backdrop} />
        <Dialog.Popup className={cart.panel}>
          <div className={cart.header}>
            <Dialog.Title className={typeScale.title}>Retailer portal</Dialog.Title>
            <Dialog.Close
              aria-label="Close menu"
              className={buttonVariants({ variant: "ghost", size: "icon" })}
            >
              <X />
            </Dialog.Close>
          </div>

          <nav className={cart.body} aria-label="Retailer">
            <p className={typeScale.meta}>Manage products, Pools, and demand from your dashboard.</p>
            <ul className="flex flex-col gap-2">
              {links.map(({ href, label, icon: Icon, description }) => (
                <li key={href}>
                  <Dialog.Close
                    render={
                      <Link href={href} className={cart.item}>
                        <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-secondary">
                          <Icon className="size-5" />
                        </span>
                        <span className="flex min-w-0 flex-col gap-0.5">
                          <span className={typeScale.title}>{label}</span>
                          <span className={typeScale.meta}>{description}</span>
                        </span>
                      </Link>
                    }
                  />
                </li>
              ))}
            </ul>
          </nav>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
