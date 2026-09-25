"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const JobsListClient = dynamic(() => import("@/components/jobs/JobsListClient"), {
  loading: () => <PageSkeleton rows={5} />,
});

export default function JobsPage() {
  return <JobsListClient />;
}
