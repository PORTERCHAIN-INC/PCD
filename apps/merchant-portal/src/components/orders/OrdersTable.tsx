"use client";

import { OrderStateBadge } from "@/components/orders/OrderStateBadge";
import type { OrderRow } from "@/lib/orders";
import { formatCents, formatDate } from "@/lib/utils";
import Link from "next/link";

type Props = {
  rows: OrderRow[];
  selected: string[];
  onSelect: (ids: string[]) => void;
};

export function OrdersTable({ rows, selected, onSelect }: Props) {
  const allSelected = rows.length > 0 && rows.every((r) => selected.includes(r.order_id));

  return (
    <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
      <table className="w-full min-w-[56rem] text-left text-sm">
        <thead className="border-b border-primary/10 bg-gray-50/80">
          <tr>
            <th className="px-3 py-3">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={(e) => onSelect(e.target.checked ? rows.map((r) => r.order_id) : [])}
                aria-label="Select all"
              />
            </th>
            <th className="px-3 py-3 font-medium">Order</th>
            <th className="px-3 py-3 font-medium">Tracking</th>
            <th className="px-3 py-3 font-medium">State</th>
            <th className="px-3 py-3 font-medium">Route</th>
            <th className="px-3 py-3 font-medium">Driver</th>
            <th className="px-3 py-3 font-medium">Amount</th>
            <th className="px-3 py-3 font-medium">Invoice</th>
            <th className="px-3 py-3 font-medium">Updated</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.order_id} className="border-b border-primary/5 hover:bg-gray-50/50">
              <td className="px-3 py-3">
                <input
                  type="checkbox"
                  checked={selected.includes(row.order_id)}
                  onChange={(e) => {
                    const id = row.order_id;
                    onSelect(
                      e.target.checked ? [...selected, id] : selected.filter((x) => x !== id)
                    );
                  }}
                />
              </td>
              <td className="px-3 py-3 font-mono text-xs">
                <Link
                  href={`/orders/${row.order_id}`}
                  className="font-semibold text-secondary hover:underline"
                >
                  {row.order_number}
                </Link>
              </td>
              <td className="px-3 py-3 font-mono text-xs">{row.tracking_number}</td>
              <td className="px-3 py-3">
                <OrderStateBadge state={row.state} />
              </td>
              <td className="max-w-[14rem] truncate px-3 py-3 text-muted">
                {row.pickup} → {row.destination}
              </td>
              <td className="px-3 py-3 text-muted">{row.driver_name ?? "—"}</td>
              <td className="px-3 py-3">
                {formatCents(row.amount_cents, row.currency.toUpperCase())}
              </td>
              <td className="px-3 py-3 capitalize text-muted">{row.invoice_status}</td>
              <td className="px-3 py-3 text-muted">{formatDate(row.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <p className="p-8 text-center text-sm text-muted">No orders match your filters.</p>
      )}
    </div>
  );
}
