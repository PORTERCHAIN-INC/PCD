"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const LeadsListClient = dynamic(() => import("@/components/leads/LeadsListClient"), {
  loading: () => <Spinner label="Loading leads…" />,
});

export default function LeadsPage() {
  return <LeadsListClient />;
}
