import { Suspense } from "react";
import BillingClient from "@/components/billing/BillingClient";

export default function BillingPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading billing…</p>}>
      <BillingClient />
    </Suspense>
  );
}
