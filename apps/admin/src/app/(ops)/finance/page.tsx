"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const FinanceCenterClient = dynamic(() => import("@/components/finance/FinanceCenterClient"), {
  loading: () => <Spinner label="Loading finance…" />,
});

export default function FinancePage() {
  return <FinanceCenterClient />;
}
