import { Suspense } from "react";
import { RetailerPoolView } from "@/components/retailer-pool-view";
import { RoleGate } from "@/components/role-gate";
import { skeleton } from "@/design/tokens";

async function Loader({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <RoleGate role="retailer">
      <RetailerPoolView poolId={Number(id)} />
    </RoleGate>
  );
}

export default function RetailerPoolPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<div className={`${skeleton} h-96`} />}>
      <Loader params={params} />
    </Suspense>
  );
}
