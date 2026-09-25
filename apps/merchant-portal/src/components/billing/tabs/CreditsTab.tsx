"use client";

import { type CreditNoteRow } from "@/lib/billing";
import { formatCents, formatDate } from "@/lib/utils";

export function CreditsTab({ credits }: { credits: CreditNoteRow[] }) {
  if (!credits.length) {
    return (
      <p className="text-sm text-muted">
        No credit notes on file. When we issue a credit, it reduces Outstanding (credits applied).
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">
        These credits are already applied to Outstanding. They reduce what you owe.
      </p>
      <ul className="space-y-3">
        {credits.map((c) => (
          <li
            key={c.credit_note_id}
            className="rounded-xl border border-primary/10 bg-white p-4 text-sm"
          >
            <p className="font-medium">{c.order_number ?? c.credit_note_id.slice(0, 8)}</p>
            <p className="text-muted">{c.reason ?? "Credit note"}</p>
            <p className="mt-1">{c.amount_cents != null ? formatCents(c.amount_cents) : "—"}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
