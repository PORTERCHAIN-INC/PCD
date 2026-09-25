"use client";

import Link from "next/link";
import type { OrderDetail } from "@/lib/orders";
import { formatCents, formatDate } from "@/lib/utils";
import { Card } from "./shared";

export function InvoiceTab({ detail }: { detail: OrderDetail }) {
  return (
    <Card title="Invoice">
      <p>Number: {detail.invoice_number ?? "Not generated"}</p>
      {detail.invoice_amount_cents != null && (
        <p className="mt-1">Amount: {formatCents(detail.invoice_amount_cents)}</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {detail.invoice_pdf_url && (
          <a
            href={detail.invoice_pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-secondary underline"
          >
            Download PDF
          </a>
        )}
        {detail.invoice_receipt_url && (
          <a
            href={detail.invoice_receipt_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-secondary underline"
          >
            Receipt
          </a>
        )}
      </div>
    </Card>
  );
}
