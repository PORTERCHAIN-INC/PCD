"use client";

import dynamic from "next/dynamic";

const InvoicesClient = dynamic(() => import("@/components/invoices/InvoicesClient"), {
  loading: () => <p className="p-8 text-sm text-muted">Loading invoices…</p>,
});

export default function InvoicesPage() {
  return <InvoicesClient />;
}
