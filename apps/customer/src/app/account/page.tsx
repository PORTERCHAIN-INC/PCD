"use client";

import dynamic from "next/dynamic";

const AccountClient = dynamic(() => import("@/components/account/AccountClient"), {
  loading: () => <p className="p-8 text-sm text-muted">Loading account…</p>,
});

export default function AccountPage() {
  return <AccountClient />;
}
