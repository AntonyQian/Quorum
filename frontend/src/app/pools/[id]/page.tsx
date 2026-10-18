import { Suspense } from "react";
import { PoolDetailView } from "@/components/pool-detail";
import { skeleton } from "@/design/tokens";

async function PoolDetailLoader({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const poolId = Number(id);
  return <PoolDetailView key={poolId} poolId={poolId} />;
}

export default function PoolPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense fallback={<div className={`${skeleton} h-96`} />}>
      <PoolDetailLoader params={params} />
    </Suspense>
  );
}
