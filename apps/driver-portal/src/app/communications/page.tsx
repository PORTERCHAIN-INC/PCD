"use client";

import dynamic from "next/dynamic";

const CommunicationsClient = dynamic(
  () => import("@/components/communications/CommunicationsClient"),
  { loading: () => <p className="p-4 text-sm text-[var(--muted)]">Loading…</p> }
);

export default function CommunicationsPage() {
  return <CommunicationsClient />;
}
