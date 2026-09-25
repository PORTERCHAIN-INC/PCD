"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const DriverDetailClient = dynamic(() => import("@/components/drivers/DriverDetailClient"), {
  loading: () => <Spinner label="Loading driver…" />,
});

export default function DriverDetailPage() {
  return <DriverDetailClient />;
}
