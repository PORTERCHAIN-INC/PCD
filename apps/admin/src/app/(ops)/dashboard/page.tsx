"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const DashboardClient = dynamic(() => import("@/components/dashboard/DashboardClient"), {
  loading: () => <Spinner label="Loading dashboard…" />,
});

export default function DashboardPage() {
  return <DashboardClient />;
}
