import { Price } from "@/components/price";
import { bar, typeScale } from "@/design/tokens";
import { formatCents } from "@/lib/money";
import {
   discountOffer,
   formatTimeLeftWords,
   membersAwayLabel,
} from "@/lib/pools";
import type { PoolSummary } from "@/lib/types";

function nextTierMeta(pool: PoolSummary, needed: number, showDeadline: boolean): string {
   const members = membersAwayLabel(needed);
   if (!showDeadline) return members;
   const time = formatTimeLeftWords(pool.time_left_seconds);
   return time === "Ended" ? `${members} · Ended` : `${members} · ${time} left`;
}

export function DiscountOffer({
   pool,
   showDeadline = false,
}: {
   pool: PoolSummary;
   showDeadline?: boolean;
}) {
   const offer = discountOffer(pool);
   const missed = pool.status === "failed";
   const nowCents = offer.active?.priceCents ?? offer.listCents;

   const progressBar = (
      <div
         className={bar.track}
         role="progressbar"
         aria-valuemin={0}
         aria-valuemax={100}
         aria-valuenow={Math.round(offer.progressPercent)}
         aria-label={
            offer.next
               ? `${membersAwayLabel(offer.next.needed)} to the next Tier`
               : offer.label
         }
      >
         <div
            className={missed ? bar.fillMuted : bar.fill}
            style={{ width: `${Math.min(offer.progressPercent, 100)}%` }}
         />
      </div>
   );

   return (
      <div className="flex flex-col gap-2">
         {offer.next ? (
            <>
               <div className="flex flex-col gap-0.5">
                  <p className={typeScale.eyebrow}>Now</p>
                  <Price
                     cents={nowCents}
                     listCents={offer.active ? offer.listCents : undefined}
                     lead
                  />
               </div>
               <div className="flex flex-col gap-1 border-t border-border pt-2">
                  <div className="flex items-baseline justify-between gap-3">
                     <p className={typeScale.eyebrow}>Next Tier</p>
                     <p className={typeScale.next}>
                        {formatCents(offer.next.priceCents)}
                     </p>
                  </div>
                  {progressBar}
                  <p className="text-xs">
                     {nextTierMeta(pool, offer.next.needed, showDeadline)}
                  </p>
               </div>
            </>
         ) : (
            <>
               <div>
                  <p className={typeScale.eyebrow}>
                     {offer.active ? "Now" : "List"}
                  </p>
                  {offer.active ? (
                     <Price
                        cents={offer.active.priceCents}
                        listCents={offer.listCents}
                        lead
                     />
                  ) : (
                     <p className={typeScale.list}>
                        {formatCents(offer.listCents)}
                     </p>
                  )}
                  <p className={`mt-0.5 ${typeScale.meta}`}>{offer.label}</p>
               </div>
               {progressBar}
            </>
         )}
      </div>
   );
}
