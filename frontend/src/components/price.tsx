import { formatCents } from "@/lib/money";
import { typeScale } from "@/design/tokens";

export function Price({
  cents,
  listCents,
  lead = false,
}: {
  cents: number;
  listCents?: number;
  lead?: boolean;
}) {
  const showList = listCents != null && listCents > cents;
  return (
    <p className="flex flex-wrap items-baseline gap-x-2">
      <span className={lead ? typeScale.priceLead : typeScale.price}>
        {formatCents(cents)}
      </span>
      {showList ? (
        <span className={typeScale.compare}>{formatCents(listCents)}</span>
      ) : null}
    </p>
  );
}
