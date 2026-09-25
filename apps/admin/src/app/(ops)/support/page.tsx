"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const SupportListClient = dynamic(() => import("@/components/support/SupportListClient"), {
  loading: () => <Spinner label="Loading support…" />,
});

export default function SupportPage() {
  return <SupportListClient />;
}
