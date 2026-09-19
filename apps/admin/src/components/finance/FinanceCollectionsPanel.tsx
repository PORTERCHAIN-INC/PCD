"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Download, ExternalLink, Mail, Phone } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { exportCollectionsCsv, type ApContact, type CollectionRow } from "@/lib/finance";
import { Button } from "@/components/crm/primitives";

type Props = {
  rows: CollectionRow[];
  onRemind?: (invoiceId: string) => void;
  remindingId?: string | null;
};

function dueLabel(due?: string | null): string {
  return due ? String(due).slice(0, 10) : "—";
}

function agingStyle(daysOverdue: number): string {
  if (daysOverdue <= 0) return "bg-gray-100 text-gray-700";
  if (daysOverdue <= 30) return "bg-amber-100 text-amber-900";
  if (daysOverdue <= 60) return "bg-orange-100 text-orange-900";
  return "bg-red-100 text-red-800";
}

/** Name plus a number you can actually dial. Falls back to the company on file. */
function ApContactCell({ contact }: { contact?: ApContact | null }) {
  if (!contact || (!contact.name && !contact.phone && !contact.email)) {
    return <span className="text-xs text-muted">No AP contact on file</span>;
  }
  return (
    <div className="space-y-0.5">
      <p className="text-xs font-medium text-primary">
        {contact.name || "—"}
        {contact.source === "company" ? (
          <span className="ml-1 font-normal text-muted">(company)</span>
        ) : null}
      </p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs">
        {contact.phone ? (
          <a
            href={`tel:${contact.phone.replace(/[^+\d]/g, "")}`}
            className="inline-flex items-center gap-1 font-medium text-secondary hover:underline"
          >
            <Phone className="h-3 w-3" />
            {contact.phone}
          </a>
        ) : (
          <span className="text-muted">No phone</span>
        )}
        {contact.email ? (
          <a
            href={`mailto:${contact.email}`}
            className="inline-flex items-center gap-1 text-secondary hover:underline"
          >
            <Mail className="h-3 w-3" />
            {contact.email}
          </a>
        ) : null}
      </div>
    </div>
  );
}

export default function FinanceCollectionsPanel({ rows, onRemind, remindingId }: Props) {
  const [bucket, setBucket] = useState("");

  // Buckets in the order the rows arrive, which is oldest debt first.
  const buckets = useMemo(() => {
    const seen: string[] = [];
    for (const r of rows) if (!seen.includes(r.aging_bucket)) seen.push(r.aging_bucket);
    return seen;
  }, [rows]);

  const visible = useMemo(
    () => (bucket ? rows.filter((r) => r.aging_bucket === bucket) : rows),
    [rows, bucket]
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={bucket}
          onChange={(e) => setBucket(e.target.value)}
          className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
        >
          <option value="">All ages</option>
          {buckets.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
        <Button variant="outline" onClick={() => exportCollectionsCsv(visible)}>
          <Download className="h-4 w-4" /> Aging CSV
        </Button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-primary/10">
        <table className="w-full min-w-[64rem] text-left text-sm">
          <thead className="border-b border-primary/10 bg-gray-bg/60">
            <tr className="text-xs font-semibold uppercase tracking-wide text-muted">
              <th className="px-3 py-2.5">Invoice</th>
              <th className="px-3 py-2.5">Merchant</th>
              <th className="px-3 py-2.5">Due</th>
              <th className="px-3 py-2.5">Aging</th>
              <th className="px-3 py-2.5 text-right">Outstanding</th>
              <th className="px-3 py-2.5">Who to call</th>
              <th className="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr
                key={r.invoice_id}
                className="border-b border-primary/5 hover:bg-secondary/[0.04]"
              >
                <td className="px-3 py-2.5">
                  <Link
                    href={`/finance/invoices/${r.invoice_id}`}
                    className="font-mono text-xs font-semibold text-secondary hover:underline"
                  >
                    {r.invoice_number}
                  </Link>
                  <p className="text-xs text-muted">{r.payment_terms}</p>
                </td>
                <td className="px-3 py-2.5">
                  {r.merchant_id ? (
                    <Link
                      href={`/merchants/${r.merchant_id}`}
                      className="text-xs font-medium text-secondary hover:underline"
                    >
                      {r.merchant_name || "Open merchant"}
                    </Link>
                  ) : (
                    <span className="text-xs text-muted">{r.merchant_name || "—"}</span>
                  )}
                </td>
                <td className="px-3 py-2.5 text-xs tabular-nums">{dueLabel(r.due_date)}</td>
                <td className="px-3 py-2.5">
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-xs font-bold",
                      agingStyle(r.days_overdue)
                    )}
                  >
                    {r.aging_bucket}
                  </span>
                  {r.days_overdue > 0 ? (
                    <p className="mt-0.5 text-xs text-muted">{r.days_overdue}d late</p>
                  ) : null}
                </td>
                <td className="px-3 py-2.5 text-right font-semibold tabular-nums text-red-600">
                  {formatCents(r.outstanding_cents)}
                </td>
                <td className="px-3 py-2.5">
                  <ApContactCell contact={r.ap_contact} />
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex items-center justify-end gap-2">
                    {onRemind ? (
                      <button
                        type="button"
                        className="text-xs font-semibold text-secondary hover:underline disabled:opacity-40"
                        disabled={remindingId === r.invoice_id}
                        onClick={() => onRemind(r.invoice_id)}
                      >
                        {remindingId === r.invoice_id ? "Sending…" : "Remind"}
                      </button>
                    ) : null}
                    <Link
                      href={`/finance/invoices/${r.invoice_id}`}
                      className="inline-flex text-secondary"
                      aria-label="Open invoice"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
