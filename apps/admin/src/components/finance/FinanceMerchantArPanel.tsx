"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatCents } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { merchants } from "@/lib/merchants";
import { financeApi } from "@/lib/finance";
import { Button, Spinner } from "@/components/crm/primitives";

export default function FinanceMerchantArPanel() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const qc = useQueryClient();
  const [merchantId, setMerchantId] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const { data: merchantRows = [], isLoading: merchantsLoading } = useQuery({
    queryKey: ["finance-ar-merchants"],
    enabled,
    queryFn: async () => merchants.list(await getApiToken(), { status: "ACTIVE" }),
  });

  const previewMut = useMutation({
    mutationFn: async () => {
      const token = await getApiToken();
      return financeApi.merchantArPreview(token, {
        merchant_id: merchantId,
        period_start: periodStart || undefined,
        period_end: periodEnd || undefined,
      });
    },
    onSuccess: () => setMessage(null),
    onError: (e: Error) => setMessage(e.message || "Preview failed"),
  });

  const generateMut = useMutation({
    mutationFn: async () => {
      const token = await getApiToken();
      return financeApi.merchantArGenerate(token, {
        merchant_id: merchantId,
        period_start: periodStart || undefined,
        period_end: periodEnd || undefined,
      });
    },
    onSuccess: async (res) => {
      setMessage(`Created ${res.created_count} invoice(s); skipped ${res.skipped_count}.`);
      await qc.invalidateQueries({ queryKey: ["finance-invoices"] });
      await qc.invalidateQueries({ queryKey: ["finance-collections"] });
      previewMut.mutate();
    },
    onError: (e: Error) => setMessage(e.message || "Generate failed"),
  });

  const preview = previewMut.data;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-semibold text-primary">Merchant cycle AR</h3>
        <p className="mt-1 text-sm text-muted">
          Preview and generate offline net-terms invoices for delivered / POD orders in a billing
          period. Leave dates empty to use the previous closed cycle for the merchant.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <label className="text-sm">
          <span className="mb-1 block text-muted">Merchant</span>
          <select
            className="w-full rounded-lg border border-primary/15 px-3 py-2"
            value={merchantId}
            disabled={merchantsLoading}
            onChange={(e) => setMerchantId(e.target.value)}
          >
            <option value="">Select merchant…</option>
            {merchantRows.map((m) => (
              <option key={m.id} value={m.id}>
                {m.company_name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-muted">Period start (optional)</span>
          <input
            type="datetime-local"
            className="w-full rounded-lg border border-primary/15 px-3 py-2"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-muted">Period end (optional)</span>
          <input
            type="datetime-local"
            className="w-full rounded-lg border border-primary/15 px-3 py-2"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
          />
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button disabled={!merchantId || previewMut.isPending} onClick={() => previewMut.mutate()}>
          {previewMut.isPending ? "Preview…" : "Preview"}
        </Button>
        <Button
          variant="outline"
          disabled={!merchantId || generateMut.isPending}
          onClick={() => generateMut.mutate()}
        >
          {generateMut.isPending ? "Generating…" : "Generate invoices"}
        </Button>
      </div>

      {message && <p className="text-sm text-secondary">{message}</p>}

      {previewMut.isPending && <Spinner />}
      {preview && (
        <div className="rounded-lg bg-gray-bg/60 p-4 text-sm">
          <p className="font-medium text-primary">
            {preview.merchant_name} · {preview.order_count} order(s) ·{" "}
            {formatCents(preview.uninvoiced_cents)}
          </p>
          <p className="mt-1 text-muted">
            Terms {preview.payment_terms || "—"} · Cycle {preview.billing_cycle || "—"} · Period{" "}
            {String(preview.period_start).slice(0, 10)} → {String(preview.period_end).slice(0, 10)}
          </p>
          {preview.orders.length > 0 && (
            <ul className="mt-3 max-h-48 space-y-1 overflow-auto">
              {preview.orders.map((o) => (
                <li key={o.order_id} className="flex justify-between gap-4 font-mono text-xs">
                  <span>
                    {o.order_number} · {o.state}
                  </span>
                  <span>{formatCents(o.amount_cents)}</span>
                </li>
              ))}
            </ul>
          )}
          {preview.order_count === 0 && (
            <p className="mt-2 text-muted">No eligible uninvoiced deliveries in this period.</p>
          )}
        </div>
      )}
    </div>
  );
}
