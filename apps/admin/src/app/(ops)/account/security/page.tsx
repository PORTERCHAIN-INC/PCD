"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const AccountSecurityClient = dynamic(() => import("@/components/account/AccountSecurityClient"), {
  loading: () => <Spinner label="Loading security…" />,
});

export default function AccountSecurityPage() {
  return <AccountSecurityClient />;
}
