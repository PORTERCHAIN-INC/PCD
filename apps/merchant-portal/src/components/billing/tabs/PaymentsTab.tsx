"use client";

import { type PaymentRow } from "@/lib/billing";
import { formatCents, formatDate } from "@/lib/utils";
import { StatusBadge } from "./shared";

export function PaymentsTab({
  payments,
  stripeEnabled,
}: {
  payments: PaymentRow[];
  stripeEnabled: boolean;
}) {
  if (!payments.length) {
    return (
      <p className="text-sm text-muted">
        No payments recorded{stripeEnabled ? "" : " — contract merchants settle on net terms"}.
      </p>
    );
  }
  return (
    <table className="w-full rounded-2xl border border-primary/10 bg-white text-left text-sm">
      <thead>
        <tr className="border-b border-primary/10 text-muted">
          <th className="px-4 py-3">Reference</th>
          <th className="px-4 py-3">Order</th>
          <th className="px-4 py-3">Method</th>
          <th className="px-4 py-3">Status</th>
          <th className="px-4 py-3">Amount</th>
          <th className="px-4 py-3">Date</th>
        </tr>
      </thead>
      <tbody>
        {payments.map((p) => (
          <tr key={p.payment_id} className="border-b border-primary/5">
            <td className="px-4 py-3 font-mono text-xs">
              {p.payment_reference ?? p.payment_id.slice(0, 8)}
            </td>
            <td className="px-4 py-3">{p.order_number ?? "—"}</td>
            <td className="px-4 py-3">{p.payment_method ?? "—"}</td>
            <td className="px-4 py-3">
              <StatusBadge status={p.status.toLowerCase()} />
            </td>
            <td className="px-4 py-3">{formatCents(p.amount_cents, p.currency.toUpperCase())}</td>
            <td className="px-4 py-3">{p.created_at ? formatDate(p.created_at) : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
