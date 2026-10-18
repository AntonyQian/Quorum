import { RetailerDashboard } from "@/components/retailer-dashboard";
import { RoleGate } from "@/components/role-gate";

export default function RetailerPage() {
  return (
    <RoleGate role="retailer">
      <RetailerDashboard />
    </RoleGate>
  );
}
