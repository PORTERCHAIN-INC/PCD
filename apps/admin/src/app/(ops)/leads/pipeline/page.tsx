"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const LeadsPipelineClient = dynamic(() => import("@/components/leads/LeadsPipelineClient"), {
  loading: () => <Spinner label="Loading…" />,
});

export default function LeadsPipelinePage() {
  return <LeadsPipelineClient />;
}
