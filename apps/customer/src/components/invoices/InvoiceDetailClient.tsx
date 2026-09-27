"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Spinner } from "@porterchain/ui/loading";
import CustomerShell from "@/components/CustomerShell";
import { customerApi } from "@/lib/api";
import { formatCents } from "@/lib/booking";
import { isClerkConfigured } from "@/lib/env";

function addressLine(addr?: Record<string, unknown> | null) {
  if (!addr) return "—";
  const parts = [
    addr.formatted || addr.street || addr.line1,
    addr.city,
    addr.postal_code || addr.postal || addr.zip,
  ].filter((part) => typeof part === "string" && part);
  return parts.join(", ") || "—";
}

export default function InvoiceDetailClient() {
  if (!isClerkConfigured()) {
    return <DetailBody getToken={async () => "dev"} />;
  }
  return <DetailWithClerk />;
}

function DetailWithClerk() {
  const router = useRouter();
  const params = useParams<{ invoice_id: string }>();
  const { isSignedIn, isLoaded, getToken } = useAuth();

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.replace(`/sign-in?redirect_url=/invoices/${params.invoice_id ?? ""}`);
    }
  }, [isLoaded, isSignedIn, params.invoice_id, router]);

  if (!isLoaded || !isSignedIn) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-gray-bg">
        <Spinner label="Loading invoice…" />
      </main>
    );
  }

  return <DetailBody getToken={getToken} />;
}

function DetailBody({ getToken }: { getToken: () => Promise<string | null> }) {
  const params = useParams<{ invoice_id: string }>();
  const invoiceId = params.invoice_id;
  const [pdfBusy, setPdfBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const { data: detail, error } = useQuery({
    queryKey: ["customer-invoice", invoiceId],
    enabled: Boolean(invoiceId),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      return customerApi.invoice(token, invoiceId);
    },
  });

  async function downloadPdf() {
    if (!detail) return;
    setPdfBusy(true);
    setNotice("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");
      await customerApi.downloadInvoicePdf(
        token,
        detail.invoice_id,
        `invoice-${detail.invoice_number}.pdf`
      );
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not download PDF");
    } finally {
      setPdfBusy(false);
    }
  }

  const currency = (detail?.currency || "cad").toUpperCase();

  return (
    <CustomerShell>
      <div className="print:hidden">
        <Link href="/invoices" className="text-sm text-secondary hover:underline">
          ← Invoices
        </Link>
      </div>
      {error ? <p className="mt-4 text-sm text-red-700">Invoice not found.</p> : null}
      {!detail && !error ? (
        <div className="mt-8 flex justify-center">
          <Spinner label="Loading invoice…" />
        </div>
      ) : null}
      {detail ? (
        <article className="invoice-sheet mt-4 rounded-2xl border border-primary/10 bg-white p-5 shadow-sm print:mt-0 print:border-0 print:shadow-none sm:p-8">
          <header className="flex flex-wrap items-start justify-between gap-4 border-b border-primary/10 pb-4">
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
              <p className="mt-1 text-sm capitalize text-muted">{detail.status}</p>
            </div>
            <div className="flex flex-wrap gap-2 print:hidden">
              <button
                type="button"
                disabled={pdfBusy}
                onClick={() => void downloadPdf()}
                className="rounded-xl border border-primary/15 px-4 py-2 text-sm font-semibold text-primary disabled:opacity-60"
              >
                {pdfBusy ? "Preparing…" : "Download PDF"}
              </button>
              <button
                type="button"
                onClick={() => window.print()}
                className="rounded-xl bg-secondary px-4 py-2 text-sm font-semibold text-white"
              >
                Print
              </button>
            </div>
          </header>
          {notice ? <p className="mt-3 text-sm text-muted print:hidden">{notice}</p> : null}
          <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-muted">Receipt</dt>
              <dd className="font-medium text-primary">{detail.receipt_number || "—"}</dd>
            </div>
            <div>
              <dt className="text-muted">Account</dt>
              <dd className="font-medium text-primary">{detail.merchant_name || "—"}</dd>
            </div>
            <div>
              <dt className="text-muted">Order</dt>
              <dd className="font-mono text-primary">{detail.order_number || "—"}</dd>
            </div>
            <div>
              <dt className="text-muted">Tracking</dt>
              <dd className="font-mono text-primary">{detail.tracking_number || "—"}</dd>
            </div>
            <div>
              <dt className="text-muted">Pickup</dt>
              <dd className="text-primary">{addressLine(detail.pickup)}</dd>
            </div>
            <div>
              <dt className="text-muted">Delivery</dt>
              <dd className="text-primary">{addressLine(detail.dropoff)}</dd>
            </div>
          </dl>
          <table className="mt-6 w-full text-left text-sm">
            <thead>
              <tr className="border-b border-primary/10 text-muted">
                <th className="py-2 font-medium">Description</th>
                <th className="py-2 font-medium">Order</th>
                <th className="py-2 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {detail.lines.map((line, index) => (
                <tr
                  key={`${line.order_number ?? "line"}-${index}`}
                  className="border-b border-primary/5"
                >
                  <td className="py-2 text-primary">{line.description}</td>
                  <td className="py-2 font-mono text-xs">{line.order_number || "—"}</td>
                  <td className="py-2 text-right">{formatCents(line.amount_cents, currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="mt-4 ml-auto max-w-xs space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted">Amount</dt>
              <dd>{formatCents(detail.amount_cents, currency)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Tax</dt>
              <dd>{formatCents(detail.tax_cents, currency)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Fees</dt>
              <dd>{formatCents(detail.fees_cents, currency)}</dd>
            </div>
            <div className="flex justify-between font-semibold text-primary">
              <dt>Outstanding</dt>
              <dd>{formatCents(detail.outstanding_cents, currency)}</dd>
            </div>
          </dl>
          {detail.stripe_receipt_url ? (
            <a
              href={detail.stripe_receipt_url}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-block text-sm font-semibold text-secondary hover:underline print:hidden"
            >
              Receipt
            </a>
          ) : null}
        </article>
      ) : null}
    </CustomerShell>
  );
}
