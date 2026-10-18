import { PoolBrowser } from "@/components/pool-browser";
import { RoleGate } from "@/components/role-gate";
import { WishBox } from "@/components/wish-box";

export default function HomePage() {
  return (
    <RoleGate role="shopper">
      <WishBox />
      <PoolBrowser />
    </RoleGate>
  );
}
