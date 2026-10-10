"use client";

import { useState } from "react";
import Link from "next/link";
import { billingApi, type InvoiceRow } from "@/lib/billing";
import { formatCents, formatDate } from "@/lib/utils";
import { StatusBadge } from "./shared";

export function InvoicesTab({
  invoices,
  orgId,
  getToken,
}: {
  invoices: InvoiceRow[];
  orgId?: string;
  getToken: () => Promise<string>;
}) {
  const [remindingId, setRemindingId] = useState<string | null>(null);
  const [pdfId, setPdfId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function openPdf(inv: InvoiceRow) {
    setPdfId(inv.invoice_id);
    setNotice(null);
    try {
      const token = await getToken();
      await billingApi.downloadInvoicePdf(
        token,
        inv.invoice_id,
        orgId,
        `invoice-${inv.invoice_number}.pdf`
      );
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Could not download that invoice PDF.");
    } finally {
      setPdfId(null);
    }
  }

  async function resend(invoiceId: string) {
    setRemindingId(invoiceId);
    setNotice(null);
    try {
      const token = await getToken();
      const result = await billingApi.remindInvoice(token, invoiceId, orgId);
      setNotice(`Reminder sent to ${result.email}`);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Could not send reminder");
    } finally {
      setRemindingId(null);
    }
  }

  if (!invoices.length) {
    return (
      <p className="text-sm text-muted">No invoices yet — net terms orders appear when invoiced.</p>
    );
  }

  return (
    <div className="space-y-2">
      {notice && <p className="text-sm text-muted">{notice}</p>}
      <div className="ops-table-scroll rounded-2xl border border-primary/10 bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b border-primary/10 text-muted">
              <th className="px-4 py-3">Invoice</th>
              <th className="px-4 py-3">Order</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Due</th>
              <th className="px-4 py-3">PDF</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.invoice_id} className="border-b border-primary/5">
                <td className="px-4 py-3 font-mono text-xs">
                  <Link
                    href={`/billing/invoices/${inv.invoice_id}`}
                    className="text-secondary hover:underline"
                  >
                    {inv.invoice_number}
                  </Link>
                </td>
                <td className="px-4 py-3">{inv.order_number ?? "—"}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={inv.status} />
                </td>
                <td className="px-4 py-3">
                  {formatCents(inv.amount_cents, inv.currency.toUpperCase())}
                  {inv.outstanding_cents > 0 && inv.status !== "paid" && (
                    <span className="ml-1 text-xs text-muted">
                      ({formatCents(inv.outstanding_cents)} due)
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">{inv.due_date ? formatDate(inv.due_date) : "—"}</td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    className="text-secondary hover:underline disabled:opacity-40"
                    disabled={pdfId === inv.invoice_id}
                    onClick={() => void openPdf(inv)}
                  >
                    {pdfId === inv.invoice_id ? "Preparing…" : "Download PDF"}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-3">
                    {inv.outstanding_cents > 0 && inv.status !== "paid" && (
                      <button
                        type="button"
                        className="text-xs font-semibold text-secondary hover:underline disabled:opacity-40"
                        disabled={remindingId === inv.invoice_id}
                        onClick={() => void resend(inv.invoice_id)}
                      >
                        {remindingId === inv.invoice_id ? "Sending…" : "Resend"}
                      </button>
                    )}
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
