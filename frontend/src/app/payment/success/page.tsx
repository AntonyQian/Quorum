import { Suspense } from "react";
import { PaymentSuccess } from "@/components/payment-success";
import { skeleton } from "@/design/tokens";

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={<div className={`${skeleton} h-32`} />}>
      <PaymentSuccess />
    </Suspense>
  );
}
