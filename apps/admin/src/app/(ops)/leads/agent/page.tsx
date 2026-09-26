"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const LeadsAgentClient = dynamic(() => import("@/components/leads/LeadsAgentClient"), {
  loading: () => <Spinner label="Loading…" />,
});

export default function LeadsAgentPage() {
  return <LeadsAgentClient />;
}
