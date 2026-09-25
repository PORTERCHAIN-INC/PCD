"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const DriversListClient = dynamic(() => import("@/components/drivers/DriversListClient"), {
  loading: () => <Spinner label="Loading drivers…" />,
});

export default function DriversPage() {
  return <DriversListClient />;
}
