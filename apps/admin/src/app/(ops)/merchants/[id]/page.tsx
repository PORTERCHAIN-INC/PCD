"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const MerchantDetailClient = dynamic(() => import("@/components/merchants/MerchantDetailClient"), {
  loading: () => <Spinner label="Loading merchant…" />,
});

export default function MerchantDetailPage() {
  return <MerchantDetailClient />;
}
