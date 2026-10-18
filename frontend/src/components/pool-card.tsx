import type { CSSProperties } from "react";
import Image from "next/image";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { DiscountOffer } from "@/components/discount-offer";
import { StatusBadge } from "@/components/status-badge";
import { glass, memberCountLabel, typeScale } from "@/design/tokens";
import { discountOffer, formatTimeLeft } from "@/lib/pools";
import type { PoolSummary } from "@/lib/types";

function timeLabel(seconds: number): string {
   const formatted = formatTimeLeft(seconds);
   return formatted === "Ended" ? formatted : `${formatted} left`;
}

export function PoolCard({ pool }: { pool: PoolSummary }) {
   const showStatus = pool.status === "completed" || pool.status === "failed";
   const hasNextTier = discountOffer(pool).next != null;

   return (
      <Link
         href={`/pools/${pool.id}`}
         className="group block rounded-xl focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none"
      >
         <Card
            className="h-full pt-0 transition-shadow group-hover:shadow-md"
            style={{ "--card-spacing": "0.5rem" } as CSSProperties}
         >
            <div className="relative aspect-[4/3]">
               <Image
                  src={pool.product.image_url}
                  alt={pool.product.name}
                  fill
                  sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                  className="object-cover"
               />
               {showStatus ? (
                  <div className="absolute top-2 left-2">
                     <StatusBadge status={pool.status} />
                  </div>
               ) : null}
               <div className="absolute inset-x-2 bottom-2">
                  <div className={glass.pill}>
                     <p
                        className={`${typeScale.title} truncate font-extrabold`}
                     >
                        {pool.product.name}
                     </p>
                     <p className={`truncate font-light text-xs`}>
                        {pool.product.retailer_name}
                     </p>
                  </div>
               </div>
            </div>
            <CardContent className="flex flex-col gap-2">
               <DiscountOffer pool={pool} showDeadline />
               {hasNextTier ? null : (
                  <p className="text-xs">
                     {memberCountLabel(pool.participants)} ·{" "}
                     {timeLabel(pool.time_left_seconds)}
                  </p>
               )}
            </CardContent>
         </Card>
      </Link>
   );
}
