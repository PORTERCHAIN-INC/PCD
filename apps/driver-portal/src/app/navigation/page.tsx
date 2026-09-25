"use client";

import dynamic from "next/dynamic";

const NavigationClient = dynamic(() => import("@/components/navigation/NavigationClient"), {
  loading: () => <p className="p-4 text-sm text-[var(--muted)]">Loading…</p>,
});

export default function NavigationPage() {
  return <NavigationClient />;
}
