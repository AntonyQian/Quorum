import Link from "next/link";
import { DemoDrawer } from "@/components/demo-drawer";
import { RoleGate } from "@/components/role-gate";
import { buttonVariants } from "@/components/ui/button";
import { layout, typeScale } from "@/design/tokens";

export default function AdminPage() {
   return (
      <RoleGate allow={["admin", "retailer"]}>
         <section className={layout.stack}>
            <div className="flex flex-col gap-2">
               <h1 className={typeScale.display}>Admin</h1>
               <p className={typeScale.meta}>
                  Sim Clock, simulated joins, demand hits, and database reset
                  for demos.
               </p>
            </div>
            <DemoDrawer />
            <div className="flex flex-wrap gap-2">
               <Link
                  href="/"
                  className={buttonVariants({ variant: "outline" })}
               >
                  Shopper home
               </Link>
               <Link
                  href="/retailer"
                  className={buttonVariants({ variant: "outline" })}
               >
                  Retailer dashboard
               </Link>
            </div>
         </section>
      </RoleGate>
   );
}
