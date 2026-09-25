"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const LeadsCalendarClient = dynamic(() => import("@/components/leads/LeadsCalendarClient"), {
  loading: () => <Spinner label="Loading…" />,
});

export default function LeadsCalendarPage() {
  return <LeadsCalendarClient />;
}
