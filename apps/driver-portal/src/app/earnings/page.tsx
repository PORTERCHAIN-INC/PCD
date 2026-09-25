"use client";

import dynamic from "next/dynamic";

const EarningsClient = dynamic(() => import("@/components/earnings/EarningsClient"), {
  loading: () => <p className="p-4 text-sm text-[var(--muted)]">Loading…</p>,
});

export default function EarningsPage() {
  return <EarningsClient />;
}
