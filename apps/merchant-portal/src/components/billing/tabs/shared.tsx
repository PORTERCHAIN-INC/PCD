"use client";

import { STATUS_STYLES } from "@/lib/billing";
import { invoiceStatusLabel, paymentStatusLabel } from "@/lib/catalog";

export const INVOICE_KEYS = new Set([
  "none",
  "generated",
  "draft",
  "pending",
  "sent",
  "paid",
  "overdue",
  "void",
  "partial",
]);

export function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-xl font-bold text-primary">{value}</p>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700";
  const label = invoiceStatusLabel(status);
  const paid = paymentStatusLabel(status);
  const text = label !== "—" && INVOICE_KEYS.has(status) ? label : paid;
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style}`}>{text}</span>;
}
