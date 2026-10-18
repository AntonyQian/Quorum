import { RoleGate } from "@/components/role-gate";
import { ShopperHome } from "@/components/shopper-home";

export default function HomePage() {
  return (
    <RoleGate role="shopper">
      <ShopperHome />
    </RoleGate>
  );
}
