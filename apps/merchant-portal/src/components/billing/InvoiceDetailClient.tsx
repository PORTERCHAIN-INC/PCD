"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { billingApi, STATUS_STYLES, type InvoiceDetail } from "@/lib/billing";
import { invoiceStatusLabel } from "@/lib/catalog";
import { formatCents, formatDate } from "@/lib/utils";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

export default function InvoiceDetailClient() {
  const { invoice_id } = useParams<{ invoice_id: string }>();
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [detail, setDetail] = useState<InvoiceDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isSignedIn || !orgId || !invoice_id) return;
    setError(null);
    try {
      const token = await getApiToken();
      const data = await billingApi.invoiceDetail(token, invoice_id, orgId);
      setDetail(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invoice not found");
      setDetail(null);
    }
  }, [getApiToken, invoice_id, isSignedIn, orgId]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !orgId) return;
    void load();
  }, [isLoaded, isSignedIn, orgId, load]);

  async function payNow() {
    if (!detail?.payable) return;
    setPaying(true);
    setNotice(null);
    try {
      const token = await getApiToken();
      const result = await billingApi.payInvoice(token, detail.invoice_id, orgId);
      if (result.pay_url) {
        window.location.href = result.pay_url;
        return;
      }
      if (result.paid) {
        setNotice("Invoice paid.");
        await load();
      }
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Could not start payment");
    } finally {
      setPaying(false);
    }
  }

  async function downloadPdf() {
    if (!detail) return;
    setPdfBusy(true);
    setNotice(null);
    try {
      const token = await getApiToken();
      await billingApi.downloadInvoicePdf(
        token,
        detail.invoice_id,
        orgId,
        `invoice-${detail.invoice_number}.pdf`
      );
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Could not download PDF");
    } finally {
      setPdfBusy(false);
    }
  }

  if (!isLoaded) return <p className="text-muted">Loading…</p>;
  if (!isSignedIn) return <p className="text-muted">Please sign in.</p>;
  if (!orgId) return <p className="text-muted">Loading company…</p>;
  if (error && !detail) return <p className="text-red-600">{error}</p>;
  if (!detail) return <p className="text-muted">Loading invoice…</p>;

  const statusClass = STATUS_STYLES[detail.status] ?? "bg-primary/10 text-primary";

  return (
    <div className="space-y-6 pb-24">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/billing?tab=invoices" className="text-sm text-secondary hover:underline">
            ← Invoices
          </Link>
          <h1 className="mt-2 font-mono text-2xl font-bold text-primary">
            {detail.invoice_number}
          </h1>
          <p className="mt-1 text-sm text-muted">
            {detail.payment_terms}
            {detail.due_date ? ` · Due ${formatDate(detail.due_date)}` : ""}
            {detail.aging_bucket ? ` · ${detail.aging_bucket}` : ""}
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusClass}`}>
          {invoiceStatusLabel(detail.status)}
        </span>
      </div>

      {notice && <p className="text-sm text-muted">{notice}</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi
          label="Amount"
          value={formatCents(detail.amount_cents, detail.currency.toUpperCase())}
        />
        <Kpi
          label="Outstanding"
          value={formatCents(detail.outstanding_cents, detail.currency.toUpperCase())}
        />
        <Kpi label="Tax" value={formatCents(detail.tax_cents, detail.currency.toUpperCase())} />
        <Kpi label="Created" value={formatDate(detail.created_at)} />
      </div>

      <section className="overflow-hidden rounded-2xl border border-primary/10 bg-white">
        <div className="border-b border-primary/10 px-4 py-3">
          <h2 className="font-semibold text-primary">Line items</h2>
          <p className="text-xs text-muted">
            Channel and pricing model explain how each cent was quoted (Quote≡Book≡Invoice).
          </p>
        </div>
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-primary/10 text-muted">
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3">Order</th>
              <th className="px-4 py-3">Channel</th>
              <th className="px-4 py-3">Pricing</th>
              <th className="px-4 py-3 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {detail.lines.map((line, idx) => (
              <tr
                key={line.line_id ?? `${line.order_id}-${idx}`}
                className="border-b border-primary/5"
              >
                <td className="px-4 py-3">{line.description}</td>
                <td className="px-4 py-3 font-mono text-xs">{line.order_number ?? "—"}</td>
                <td className="px-4 py-3 capitalize">{line.channel ?? "—"}</td>
                <td className="px-4 py-3 uppercase">{line.pricing_model ?? "—"}</td>
                <td className="px-4 py-3 text-right">
                  {formatCents(line.amount_cents, detail.currency.toUpperCase())}
                  {line.rate_quote_cents != null && (
                    <span className="mt-0.5 block text-xs text-muted">
                      Quote {formatCents(line.rate_quote_cents)}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {detail.remittance_memo && (
        <p className="text-sm text-muted">
          Remittance memo: <span className="font-mono text-primary">{detail.remittance_memo}</span>
        </p>
      )}

      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-primary/10 bg-white/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-primary">
              {formatCents(detail.outstanding_cents, detail.currency.toUpperCase())} outstanding
            </p>
            <p className="text-xs text-muted">{detail.invoice_number}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={pdfBusy}
              onClick={() => void downloadPdf()}
            >
              {pdfBusy ? "Preparing…" : "Download PDF"}
            </Button>
            {detail.payable && (
              <Button size="sm" disabled={paying} onClick={() => void payNow()}>
                {paying ? "Opening…" : "Pay now"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-primary">{value}</p>
    </div>
  );
}
