"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const MerchantsListClient = dynamic(() => import("@/components/merchants/MerchantsListClient"), {
  loading: () => <Spinner label="Loading merchants…" />,
});

export default function MerchantsPage() {
  return <MerchantsListClient />;
}
