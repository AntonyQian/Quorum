import { ProductForm } from "@/components/product-form";
import { RoleGate } from "@/components/role-gate";

export default function NewProductPage() {
  return (
    <RoleGate role="retailer">
      <ProductForm />
    </RoleGate>
  );
}
