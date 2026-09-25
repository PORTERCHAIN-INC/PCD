"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const LeadDetailClient = dynamic(() => import("@/components/leads/LeadDetailClient"), {
  loading: () => <Spinner label="Loading lead…" />,
});

export default function LeadDetailPage(props: { params: Promise<{ id: string }> }) {
  return <LeadDetailClient {...props} />;
}
