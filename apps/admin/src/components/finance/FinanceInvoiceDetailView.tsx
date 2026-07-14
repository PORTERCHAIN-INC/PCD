"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import {
  INVOICE_STATUS_STYLES,
  PAYMENT_STATUS_STYLES,
  financeApi,
  type InvoiceDetail,
} from "@/lib/finance";
import { relativeTime } from "@/lib/crmFormat";
import { Button, Spinner } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";

type Props = { detail: InvoiceDetail | null; loading: boolean };

export default function FinanceInvoiceDetailView({ detail, loading }: Props) {
  const { getApiToken } = useAdminAuth();
  const qc = useQueryClient();
  const [method, setMethod] = useState("wire");
  const [reference, setReference] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const payMut = useMutation({
    mutationFn: async () => {
      if (!detail) throw new Error("no_invoice");
      return financeApi.recordPayment(await getApiToken(), detail.invoice_id, {
        method,
        reference: reference || undefined,
      });
    },
    onSuccess: async () => {
      setMsg("Payment recorded.");
      await qc.invalidateQueries({ queryKey: ["finance-invoice", detail?.invoice_id] });
      await qc.invalidateQueries({ queryKey: ["finance-invoices"] });
      await qc.invalidateQueries({ queryKey: ["finance-collections"] });
    },
    onError: (e: Error) => setMsg(e.message || "Record payment failed"),
  });

  if (loading)
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  if (!detail) return <p className="py-12 text-center text-muted">Invoice not found</p>;

  const payment = detail.payment as Record<string, unknown> | null | undefined;
  const canRecord =
    detail.outstanding_cents > 0 && detail.status !== "paid" && detail.status !== "void";

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/finance"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted hover:text-secondary"
        >
          <ArrowLeft className="h-4 w-4" /> Back to finance
        </Link>
        <h1 className="font-mono text-2xl font-bold text-primary">{detail.invoice_number}</h1>
        <span
          className={cn(
            "mt-2 inline-block rounded-full px-2.5 py-0.5 text-xs font-bold capitalize",
            INVOICE_STATUS_STYLES[detail.status] ?? "bg-gray-100"
          )}
        >
          {detail.status.replace(/_/g, " ")}
        </span>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-primary/10 bg-white p-6"
        >
          <h2 className="mb-3 font-semibold">Invoice</h2>
          <Row label="Amount" value={formatCents(detail.amount_cents)} />
          <Row label="Outstanding" value={formatCents(detail.outstanding_cents)} />
          <Row label="Tax" value={formatCents(detail.tax_cents)} />
          <Row label="Merchant" value={detail.merchant_name || "—"} />
          <Row label="Customer" value={detail.customer_email || "—"} />
          <Row label="Order" value={detail.order_number || "—"} mono />
          <Row label="Tracking" value={detail.tracking_number || "—"} mono />
          <Row label="Terms" value={detail.payment_terms} />
          {detail.pdf_url && (
            <a
              href={detail.pdf_url}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-block text-sm text-secondary hover:underline"
            >
              Download PDF
            </a>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-primary/10 bg-white p-6"
        >
          <h2 className="mb-3 font-semibold">Payment</h2>
          {payment ? (
            <>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-bold",
                  PAYMENT_STATUS_STYLES[String(payment.status)] ?? "bg-gray-100"
                )}
              >
                {String(payment.status)}
              </span>
              <Row label="Amount" value={formatCents(Number(payment.amount_cents))} />
              <Row label="Method" value={String(payment.payment_method || "—")} />
              <Row label="Reference" value={String(payment.payment_reference || "—")} mono />
              {payment.receipt_url ? (
                <a
                  href={String(payment.receipt_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-secondary hover:underline"
                >
                  Receipt
                </a>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-muted">No payment linked</p>
          )}

          {canRecord && (
            <div className="mt-4 space-y-2 border-t border-primary/10 pt-4">
              <p className="text-sm font-medium text-primary">Record offline payment</p>
              <select
                className="w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
              >
                <option value="wire">Wire</option>
                <option value="ach">ACH</option>
                <option value="cheque">Cheque</option>
                <option value="other">Other</option>
              </select>
              <input
                className="w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
                placeholder="Reference (optional)"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
              />
              <Button disabled={payMut.isPending} onClick={() => payMut.mutate()}>
                {payMut.isPending
                  ? "Recording…"
                  : `Record ${formatCents(detail.outstanding_cents)}`}
              </Button>
              {msg && <p className="text-xs text-secondary">{msg}</p>}
            </div>
          )}
        </motion.div>
      </div>

      <div className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="mb-3 font-semibold">Financial timeline</h2>
        <ol className="relative border-l-2 border-secondary/20 pl-6">
          {detail.timeline.map((e, i) => (
            <li key={i} className="relative mb-4">
              <span className="absolute -left-[25px] mt-1 h-3 w-3 rounded-full bg-secondary" />
              <p className="font-medium text-primary">{String(e.label || e.event_type)}</p>
              <p className="text-xs text-muted">
                {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
              </p>
            </li>
          ))}
          {!detail.timeline.length && <p className="text-sm text-muted">No events recorded</p>}
        </ol>
      </div>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4 border-b border-primary/5 py-2 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className={cn("text-right text-primary", mono && "font-mono text-xs")}>{value}</span>
    </div>
  );
}
