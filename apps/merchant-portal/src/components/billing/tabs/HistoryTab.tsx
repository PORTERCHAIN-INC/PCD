"use client";

import { type BillingHistoryRow } from "@/lib/billing";
import { formatCents, formatDate } from "@/lib/utils";

export function HistoryTab({ history }: { history: BillingHistoryRow[] }) {
  if (!history.length) return <p className="text-sm text-muted">No billing history yet.</p>;
  return (
    <ul className="divide-y divide-primary/10 rounded-2xl border border-primary/10 bg-white">
      {history.map((h) => (
        <li
          key={`${h.kind}-${h.id}`}
          className="flex items-center justify-between gap-4 px-4 py-3 text-sm"
        >
          <div>
            <p className="font-medium capitalize">{h.kind.replace("_", " ")}</p>
            <p className="text-muted">{h.description}</p>
          </div>
          <div className="text-right">
            <p className={h.amount_cents < 0 ? "text-green-700" : ""}>
              {formatCents(Math.abs(h.amount_cents))}
            </p>
            <p className="text-xs text-muted">
              {h.occurred_at ? formatDate(String(h.occurred_at)) : ""}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
