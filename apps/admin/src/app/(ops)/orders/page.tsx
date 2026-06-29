"use client";

import { useState } from "react";
import { DataTable } from "@/components/DataTable";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { api, type OrderDetail } from "@/lib/api";
import { formatCents } from "@porterchain/ui/utils";

const PAYMENT_STATUS_STYLES: Record<string, string> = {
  SUCCEEDED: "bg-green-100 text-green-700",
  PROCESSING: "bg-amber-100 text-amber-700",
  PENDING: "bg-gray-100 text-gray-600",
  FAILED: "bg-red-100 text-red-700",
};

export default function OrdersPage() {
  const { data } = useApiData((t) => api.orders(t));
  const { getApiToken } = useAdminAuth();
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const orders = data || [];

  async function openDetail(index: number) {
    const order = orders[index];
    if (!order?.order_id) return;
    setLoadingDetail(true);
    try {
      const token = await getApiToken();
      const result = await api.orderDetail(token, String(order.order_id));
      setDetail(result);
    } catch {
      setDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-primary">Order Management</h1>
        <p className="text-sm text-muted">Click an order to view stored pricing &amp; payment</p>
      </div>
      <DataTable
        columns={["Tracking", "State", "Amount", "Scheduled"]}
        rows={orders.map((o) => [
          String(o.tracking_number),
          String(o.state),
          formatCents(Number(o.amount_cents)),
          String(o.scheduled_at).slice(0, 16),
        ])}
        onRowClick={openDetail}
      />

      {(detail || loadingDetail) && (
        <OrderDetailDrawer
          detail={detail}
          loading={loadingDetail}
          onClose={() => setDetail(null)}
        />
      )}
    </div>
  );
}

function OrderDetailDrawer({
  detail,
  loading,
  onClose,
}: {
  detail: OrderDetail | null;
  loading: boolean;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative h-full w-full max-w-md overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 flex items-center justify-between border-b border-primary/10 bg-white px-5 py-4">
          <h2 className="text-lg font-bold text-primary">Order details</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full px-3 py-1 text-sm text-muted hover:bg-gray-bg"
          >
            Close
          </button>
        </div>

        {loading && <p className="p-6 text-sm text-muted">Loading…</p>}

        {detail && (
          <div className="space-y-6 p-5">
            <Section title="Summary">
              <Row label="Order #" value={detail.order_number} />
              <Row label="Tracking" value={detail.tracking_number} />
              <Row label="State" value={detail.state} />
              <Row label="Total charged" value={formatCents(detail.amount_cents)} strong />
              <Row label="Scheduled" value={detail.scheduled_at.slice(0, 16)} />
              {detail.booking_number && <Row label="Booking #" value={detail.booking_number} />}
            </Section>

            <Section title="Customer">
              <Row label="Email" value={detail.customer_email ?? "—"} />
              <Row label="Phone" value={detail.customer_phone ?? "—"} />
            </Section>

            <Section title="Shipment">
              <Row label="Pickup" value={addr(detail.pickup)} />
              <Row label="Dropoff" value={addr(detail.dropoff)} />
              <Row label="Vehicle" value={detail.vehicle_class ?? "—"} />
              <Row label="Package" value={detail.package_type ?? "—"} />
              {detail.weight_kg != null && <Row label="Weight" value={`${detail.weight_kg} kg`} />}
              {detail.dimensions && <Row label="Dimensions" value={detail.dimensions} />}
              {detail.distance_meters != null && (
                <Row label="Distance" value={`${(detail.distance_meters / 1000).toFixed(1)} km`} />
              )}
              {detail.special_instructions && (
                <Row label="Instructions" value={detail.special_instructions} />
              )}
            </Section>

            <Section title="Pricing breakdown (at booking)">
              {detail.pricing_breakdown?.items?.length ? (
                <div className="space-y-1.5">
                  {detail.pricing_breakdown.items.map((line) => (
                    <div key={line.code} className="flex items-center justify-between text-sm">
                      <span className="text-muted">{line.label}</span>
                      <span className="font-medium tabular-nums text-primary">
                        {formatCents(line.amount_cents)}
                      </span>
                    </div>
                  ))}
                  <div className="mt-2 flex items-center justify-between border-t border-primary/10 pt-2 text-sm font-bold">
                    <span>Total</span>
                    <span className="tabular-nums">
                      {formatCents(detail.quote_amount_cents ?? detail.amount_cents)}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted">No breakdown stored.</p>
              )}
              {detail.pricing_breakdown?.summary && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs font-medium text-secondary">
                    Engine summary (raw)
                  </summary>
                  <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-gray-bg p-3 text-[11px] leading-relaxed text-primary">
                    {JSON.stringify(detail.pricing_breakdown.summary, null, 2)}
                  </pre>
                </details>
              )}
            </Section>

            <Section title="Payment">
              {detail.payments.length ? (
                detail.payments.map((p) => (
                  <div
                    key={p.payment_id}
                    className="rounded-xl border border-primary/10 p-3 text-sm"
                  >
                    <div className="mb-1 flex items-center justify-between">
                      <span
                        className={
                          "rounded-full px-2 py-0.5 text-xs font-bold " +
                          (PAYMENT_STATUS_STYLES[p.status] ?? "bg-gray-100 text-gray-600")
                        }
                      >
                        {p.status}
                      </span>
                      <span className="font-semibold tabular-nums">
                        {formatCents(p.amount_cents)}
                      </span>
                    </div>
                    {p.stripe_payment_intent_id && (
                      <Row label="Payment intent" value={p.stripe_payment_intent_id} mono />
                    )}
                    {p.stripe_checkout_session_id && (
                      <Row label="Checkout session" value={p.stripe_checkout_session_id} mono />
                    )}
                    {p.failure_reason && <Row label="Failure" value={p.failure_reason} />}
                    {p.retry_count > 0 && <Row label="Retries" value={String(p.retry_count)} />}
                    {p.receipt_url && (
                      <a
                        href={p.receipt_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs font-medium text-secondary hover:underline"
                      >
                        View receipt
                      </a>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted">No payment recorded.</p>
              )}
            </Section>

            {detail.invoice_number && (
              <Section title="Invoice">
                <Row label="Invoice #" value={detail.invoice_number} />
                {detail.invoice_amount_cents != null && (
                  <Row label="Amount" value={formatCents(detail.invoice_amount_cents)} />
                )}
                {detail.invoice_receipt_url && (
                  <a
                    href={detail.invoice_receipt_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-medium text-secondary hover:underline"
                  >
                    Stripe receipt
                  </a>
                )}
                {detail.invoice_pdf_url && (
                  <a
                    href={detail.invoice_pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-3 text-xs font-medium text-secondary hover:underline"
                  >
                    PDF
                  </a>
                )}
              </Section>
            )}

            {detail.fleetbase_order_id && (
              <Section title="Dispatch">
                <Row label="Fleetbase order" value={detail.fleetbase_order_id} mono />
                {detail.assigned_driver_id && (
                  <Row label="Driver" value={detail.assigned_driver_id} mono />
                )}
              </Section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">{title}</h3>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function Row({
  label,
  value,
  strong,
  mono,
}: {
  label: string;
  value: string;
  strong?: boolean;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 text-sm">
      <span className="shrink-0 text-muted">{label}</span>
      <span
        className={
          "text-right text-primary" +
          (strong ? " font-bold" : "") +
          (mono ? " break-all font-mono text-xs" : "")
        }
      >
        {value}
      </span>
    </div>
  );
}

function addr(a: Record<string, unknown> | null | undefined): string {
  if (!a) return "—";
  return String(a.formatted ?? a.address ?? "—");
}
