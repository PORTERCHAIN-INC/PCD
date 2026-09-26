"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const LeadsTodayClient = dynamic(() => import("@/components/leads/LeadsTodayClient"), {
  loading: () => <Spinner label="Loading…" />,
});

export default function LeadsTodayPage() {
  return <LeadsTodayClient />;
}
