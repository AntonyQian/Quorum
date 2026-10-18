import { OrdersView } from "@/components/orders-view";
import { RoleGate } from "@/components/role-gate";

export default function OrdersPage() {
  return (
    <RoleGate role="shopper">
      <OrdersView />
    </RoleGate>
  );
}
