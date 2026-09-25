"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const DashboardClient = dynamic(() => import("./DashboardClient"), {
  loading: () => <PageSkeleton rows={5} />,
});

export default function DashboardPage() {
  return <DashboardClient />;
}
