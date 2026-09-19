"use client";

import { useState } from "react";
import { ExternalLink, FileText } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { downloadOrderFile, ordersApi, type OrderDetail } from "@/lib/orders";
import { ActionFlash } from "@/components/orders/sections/ActionFlash";

/** Shared invoice/shipment download actions for drawer Money + full-page Evidence/Money. */
export function OrderMoneyDownloads({ detail }: { detail: OrderDetail }) {
  const { getApiToken } = useAdminAuth();
  const [error, setError] = useState<string | null>(null);

  async function run(label: string, path: string, filename: string) {
    setError(null);
    try {
      const token = await getApiToken();
      await downloadOrderFile(token, path, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} failed`);
    }
  }

  return (
    <div className="space-y-2">
      <ActionFlash error={error} />
      <div className="flex flex-wrap gap-3">
        {detail.invoice_receipt_url ? (
          <a
            href={detail.invoice_receipt_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs font-medium text-secondary hover:underline"
          >
            Receipt <ExternalLink className="h-3 w-3" />
          </a>
        ) : null}
        {detail.invoice_pdf_url ? (
          <a
            href={detail.invoice_pdf_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs font-medium text-secondary hover:underline"
          >
            <FileText className="h-3.5 w-3.5" /> Invoice PDF
          </a>
        ) : detail.invoice_number ? (
          <button
            type="button"
            className="inline-flex items-center gap-1 text-xs font-medium text-secondary hover:underline"
            onClick={() =>
              void run(
                "Invoice PDF",
                ordersApi.invoicePdfUrl(detail.order_id),
                `invoice-${detail.invoice_number}.pdf`
              )
            }
          >
            <FileText className="h-3.5 w-3.5" /> Invoice PDF
          </button>
        ) : null}
        <button
          type="button"
          className="inline-flex items-center gap-1 text-xs font-medium text-secondary hover:underline"
          onClick={() =>
            void run(
              "Shipment record",
              ordersApi.compliancePdfUrl(detail.order_id),
              `shipment-${detail.order_number}.pdf`
            )
          }
        >
          Shipment record
        </button>
      </div>
    </div>
  );
}
