"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const ClaimsListClient = dynamic(() => import("@/components/claims/ClaimsListClient"), {
  loading: () => <Spinner label="Loading claims…" />,
});

export default function ClaimsPage() {
  return <ClaimsListClient />;
}
