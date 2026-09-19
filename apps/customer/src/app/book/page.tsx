import { Suspense } from "react";
import CustomerShell from "@/components/CustomerShell";
import CustomerBookDelivery from "@/components/booking/CustomerBookDelivery";

export default function BookPage() {
  return (
    <CustomerShell>
      <Suspense fallback={<p className="p-8 text-sm text-muted">Loading booking…</p>}>
        <CustomerBookDelivery />
      </Suspense>
    </CustomerShell>
  );
}
