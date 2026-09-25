"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const CustomerDetailClient = dynamic(() => import("@/components/customers/CustomerDetailClient"), {
  loading: () => <Spinner label="Loading customer…" />,
});

export default function CustomerDetailPage() {
  return <CustomerDetailClient />;
}
