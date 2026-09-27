"use client";

import dynamic from "next/dynamic";

const InvoiceDetailClient = dynamic(() => import("@/components/invoices/InvoiceDetailClient"), {
  loading: () => <p className="p-8 text-sm text-muted">Loading invoice…</p>,
});

export default function InvoiceDetailPage() {
  return <InvoiceDetailClient />;
}
