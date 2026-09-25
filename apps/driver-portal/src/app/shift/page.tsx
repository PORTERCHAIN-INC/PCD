"use client";

import dynamic from "next/dynamic";

const ShiftClient = dynamic(() => import("@/components/shift/ShiftClient"), {
  loading: () => <p className="p-4 text-sm text-[var(--muted)]">Loading…</p>,
});

export default function ShiftPage() {
  return <ShiftClient />;
}
