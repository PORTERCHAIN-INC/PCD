"use client";

import dynamic from "next/dynamic";

const JobsListClient = dynamic(() => import("@/components/jobs/JobsListClient"), {
  loading: () => <p className="p-4 text-sm text-[var(--muted)]">Loading…</p>,
});

export default function JobsPage() {
  return <JobsListClient />;
}
