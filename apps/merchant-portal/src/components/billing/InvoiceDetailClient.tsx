"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { billingApi, STATUS_STYLES } from "@/lib/billing";
import { invoiceStatusLabel } from "@/lib/catalog";
import { formatCents, formatDate } from "@/lib/utils";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

export default function InvoiceDetailClient({ invoiceId }: { invoiceId: string }) {
  const invoice_id = invoiceId;
  const { getApiToken, orgId, isLoaded, isSignedIn, session } = useMerchantAuth();
  const [pdfBusy, setPdfBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const enabled = Boolean(isLoaded && isSignedIn && orgId && invoice_id);
  const {
    data: detail,
    error: queryError,
    isLoading,
  } = useQuery({
    queryKey: ["merchant-invoice", orgId ?? null, invoice_id],
    enabled,
    staleTime: 60_000,
    queryFn: async () => billingApi.invoiceDetail(await getApiToken(), invoice_id, orgId),
  });

  const error =
    queryError instanceof Error ? queryError.message : queryError ? "Invoice not found" : null;

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

  if (isLoaded && !isSignedIn) return <p className="text-muted">Please sign in.</p>;
  if (error && !detail) return <p className="text-red-600">{error}</p>;
  if (!detail && (isLoading || !isLoaded || !orgId)) return <PageSkeleton rows={5} />;
  if (!detail) return null;

  const statusClass = STATUS_STYLES[detail.status] ?? "bg-primary/10 text-primary";
  const currency = detail.currency.toUpperCase();

  return (
    <div className="space-y-6 pb-24 print:pb-0">
      <div className="print:hidden">
        <Link href="/billing?tab=invoices" className="text-sm text-secondary hover:underline">
          ← Invoices
        </Link>
      </div>

      {notice && <p className="text-sm text-muted print:hidden">{notice}</p>}

      <article className="invoice-sheet space-y-6 rounded-2xl border border-primary/10 bg-white p-5 shadow-sm print:border-0 print:shadow-none sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-primary/10 pb-4">
          <div>
            <p className="flex items-center gap-2 text-sm font-semibold tracking-tight text-primary">
              <img
                src="/brand/porterchain-mark.png"
                alt=""
                width={32}
                height={28}
                className="h-8 w-auto"
              />
              porterchain
            </p>
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

        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted">From</dt>
            <dd className="font-medium text-primary">Porterchain Logistics Inc.</dd>
          </div>
          <div>
            <dt className="text-muted">Bill to</dt>
            <dd className="font-medium text-primary">{session?.company_name || "Your company"}</dd>
          </div>
          <div>
            <dt className="text-muted">Issued</dt>
            <dd className="text-primary">{formatDate(detail.created_at)}</dd>
          </div>
          <div>
            <dt className="text-muted">Outstanding</dt>
            <dd className="font-semibold text-primary">
              {formatCents(detail.outstanding_cents, currency)}
            </dd>
          </div>
        </dl>

        <div className="grid gap-4 sm:grid-cols-3">
          <Kpi label="Amount" value={formatCents(detail.amount_cents, currency)} />
          <Kpi label="Tax" value={formatCents(detail.tax_cents, currency)} />
          <Kpi label="Fees" value={formatCents(detail.fees_cents, currency)} />
        </div>

        <section className="overflow-hidden rounded-2xl border border-primary/10">
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
                  <td className="px-4 py-3">
                    {line.description}
                    {line.evidence ? (
                      <details className="mt-1 text-xs text-primary/70">
                        <summary className="cursor-pointer">Evidence</summary>
                        {line.evidence.stops?.map((s) => (
                          <p key={s.arrived}>
                            {s.kind}: arrived {new Date(s.arrived).toLocaleString()}, done{" "}
                            {new Date(s.done).toLocaleTimeString()} ({s.minutes} min)
                          </p>
                        ))}
                        {line.evidence.state ? (
                          <p>
                            Status {line.evidence.state}
                            {line.evidence.failed_at
                              ? ` at ${new Date(line.evidence.failed_at).toLocaleString()}`
                              : ""}
                            {line.evidence.reason ? ` · ${line.evidence.reason}` : ""}
                          </p>
                        ) : null}
                        <p>Source: {line.evidence.source || "driver app records"}</p>
                      </details>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{line.order_number ?? "—"}</td>
                  <td className="px-4 py-3 capitalize">{line.channel ?? "—"}</td>
                  <td className="px-4 py-3 uppercase">{line.pricing_model ?? "—"}</td>
                  <td className="px-4 py-3 text-right">
                    {formatCents(line.amount_cents, currency)}
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
            Remittance memo:{" "}
            <span className="font-mono text-primary">{detail.remittance_memo}</span>
          </p>
        )}
      </article>

      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-primary/10 bg-white/95 px-4 py-3 backdrop-blur print:hidden">
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
            <Button variant="outline" size="sm" onClick={() => window.print()}>
              Print
            </Button>
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
