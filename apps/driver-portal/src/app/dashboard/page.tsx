"use client";

import dynamic from "next/dynamic";

const DashboardClient = dynamic(() => import("@/components/dashboard/DashboardClient"), {
  loading: () => <p className="p-4 text-sm text-[var(--muted)]">Loading…</p>,
});

export default function DashboardPage() {
  return <DashboardClient />;
}
