import { bar } from "@/design/tokens";
import { tierProgress } from "@/lib/pools";
import type { PoolSummary } from "@/lib/types";

export function TierProgressBar({ pool }: { pool: PoolSummary }) {
  const progress = tierProgress(pool);
  const scale = pool.stock_cap ?? pool.tiers[pool.tiers.length - 1]?.min_participants ?? pool.participants;

  return (
    <div
      className="relative mt-3 mb-8"
      role="progressbar"
      aria-valuemin={0}
      aria-valuenow={pool.participants}
      aria-valuemax={scale}
      aria-label="Members toward each Tier"
    >
      <div className={bar.track}>
        <div
          className={bar.fill}
          style={{ width: `${Math.min(progress.fillPercent, 100)}%` }}
        />
      </div>
      {progress.markers.map((marker) => {
        const tier = pool.tiers.find((entry) => entry.ordinal === marker.ordinal);
        return (
          <div
            key={marker.ordinal}
            className="absolute top-0 flex -translate-x-1/2 flex-col items-center"
            style={{ left: `${marker.percent}%` }}
          >
            <span
              className={marker.reached ? bar.markerReached : bar.marker}
            />
            <span className={bar.markerLabel}>{tier?.min_participants}</span>
          </div>
        );
      })}
    </div>
  );
}
