"use client";

import { useState } from "react";
import Link from "next/link";
import { billingApi } from "@/lib/billing";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import type { OrderDetail } from "@/lib/orders";
import { formatCents } from "@/lib/utils";
import { Card } from "./shared";

export function InvoiceTab({ detail }: { detail: OrderDetail }) {
  const { getApiToken, orgId } = useMerchantAuth();
  const [pdfBusy, setPdfBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function downloadPdf() {
    if (!detail.invoice_id) return;
    setPdfBusy(true);
    setNotice(null);
    try {
      const token = await getApiToken();
      await billingApi.downloadInvoicePdf(
        token,
        detail.invoice_id,
        orgId,
        `invoice-${detail.invoice_number ?? detail.invoice_id}.pdf`
      );
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not download PDF");
    } finally {
      setPdfBusy(false);
    }
  }

  return (
    <Card title="Invoice">
      <p>Number: {detail.invoice_number ?? "Not generated"}</p>
      {detail.invoice_amount_cents != null && (
        <p className="mt-1">Amount: {formatCents(detail.invoice_amount_cents)}</p>
      )}
      <div className="mt-3 flex flex-wrap gap-3">
        {detail.invoice_id ? (
          <Link
            href={`/billing/invoices/${detail.invoice_id}`}
            className="text-secondary underline"
          >
            Open invoice
          </Link>
        ) : null}
        {detail.invoice_id ? (
          <button
            type="button"
            className="text-secondary underline disabled:opacity-40"
            disabled={pdfBusy}
            onClick={() => void downloadPdf()}
          >
            {pdfBusy ? "Preparing…" : "Download PDF"}
          </button>
        ) : null}
        {detail.invoice_receipt_url ? (
          <a
            href={detail.invoice_receipt_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-secondary underline"
          >
            Receipt
          </a>
        ) : null}
      </div>
      {notice ? <p className="mt-2 text-xs text-muted">{notice}</p> : null}
    </Card>
  );
}
