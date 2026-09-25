import dynamic from "next/dynamic";
import { Suspense } from "react";
import CustomerShell from "@/components/CustomerShell";

const CustomerBookDelivery = dynamic(() => import("@/components/booking/CustomerBookDelivery"), {
  loading: () => <p className="p-8 text-sm text-muted">Loading booking…</p>,
});

export default function BookPage() {
  return (
    <CustomerShell>
      <Suspense fallback={<p className="p-8 text-sm text-muted">Loading booking…</p>}>
        <CustomerBookDelivery />
      </Suspense>
    </CustomerShell>
  );
}
