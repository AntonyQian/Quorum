import { Badge } from "@/components/ui/badge";
import { poolStatus } from "@/design/tokens";
import type { PoolStatus } from "@/lib/types";
import { cn } from "cn";

export function StatusBadge({ status }: { status: PoolStatus }) {
  const treatment = poolStatus[status];
  return (
    <Badge className={cn(treatment.badge)}>{treatment.label}</Badge>
  );
}
