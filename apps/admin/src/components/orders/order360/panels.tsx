"use client";

import { type ReactNode } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { orderSourceLabel, shopifyAdminUrl, type OrderDetail } from "@/lib/orders";
import { dateTime, money, relativeTime, titleCase } from "@/lib/crmFormat";
import { Badge, EmptyState } from "@/components/crm/primitives";
import { PodDownloadAll, PodDownloadOne } from "@/components/orders/PodDownloads";
import { OrderMoneyDownloads } from "@/components/orders/sections";
import { paymentTone, pickupWindowFromStops, str, Strip } from "./shared";

export function DetailsTab({ detail }: { detail: OrderDetail }) {
  const rows: [string, ReactNode][] = [
    ["Merchant", detail.merchant_name ?? "—"],
    ["Customer", [detail.customer_email, detail.customer_phone].filter(Boolean).join(" · ") || "—"],
    [
      "Driver",
      detail.driver_name
        ? `${detail.driver_name}${detail.driver_status ? ` · ${titleCase(detail.driver_status)}` : ""}`
        : "Unassigned",
    ],
    ["Vehicle", detail.vehicle_label ?? titleCase(detail.vehicle_class) ?? "—"],
    ["Scheduled", dateTime(detail.scheduled_at)],
    ...(pickupWindowFromStops(detail.stops)
      ? ([["Pickup window", pickupWindowFromStops(detail.stops)]] as [string, ReactNode][])
      : []),
    ["Service", titleCase(detail.service_type)],
    [
      "Package",
      [
        titleCase(detail.package_type),
        detail.weight_kg != null ? `${detail.weight_kg} kg` : null,
        detail.parcel_count != null ? `${detail.parcel_count} parcel(s)` : null,
      ]
        .filter((v) => v && v !== "—")
        .join(" · ") || "—",
    ],
    [
      "Quoted distance",
      detail.distance_meters != null ? `${(detail.distance_meters / 1000).toFixed(1)} km` : "—",
    ],
    ["Instructions", detail.special_instructions ?? "—"],
    ["Source", detail.order_source_label || orderSourceLabel(detail.order_source)],
    ...(detail.shopify
      ? ([
          ["Shopify order", detail.shopify.order_name || detail.shopify.order_id || "—"],
          ["Shop", detail.shopify.shop_domain || "—"],
          ["Fulfillment", detail.shopify.fulfillment_id || "Not created yet"],
          [
            "Last tracking event",
            detail.shopify.last_event_status
              ? titleCase(detail.shopify.last_event_status)
              : "Not sent yet",
          ],
          [
            "Shopify admin",
            detail.shopify.order_admin_url || shopifyAdminUrl(detail.shopify) ? (
              <a
                className="text-secondary hover:underline"
                href={
                  detail.shopify.order_admin_url || shopifyAdminUrl(detail.shopify) || undefined
                }
                target="_blank"
                rel="noopener noreferrer"
              >
                Open order
              </a>
            ) : (
              "—"
            ),
          ],
        ] as [string, ReactNode][])
      : ([
          ["PO", detail.purchase_order_number ?? "—"],
          ["Internal", detail.internal_reference ?? "—"],
        ] as [string, ReactNode][])),
    ["Cost centre", detail.cost_centre ?? "—"],
    [
      "Fleetbase ID",
      detail.fleetbase_order_id ? (
        <span className="font-mono text-xs">{detail.fleetbase_order_id}</span>
      ) : (
        "Not synced"
      ),
    ],
  ];
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</dt>
          <dd className="mt-0.5 text-sm text-primary">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function TimelineTab({ detail }: { detail: OrderDetail }) {
  if (detail.timeline.length === 0) return <EmptyState title="No timeline events yet" />;
  return (
    <div className="divide-y divide-primary/5">
      {detail.timeline.map((t, i) => {
        const label =
          str(t["label"]) ??
          str(t["event_type"]) ??
          str(t["to_state"]) ??
          str(t["state"]) ??
          "Event";
        const when = str(t["created_at"]) ?? str(t["occurred_at"]);
        const actor = str(t["actor_type"]) ?? str(t["actor"]);
        return (
          <div key={i} className="flex items-center justify-between py-2.5">
            <div className="flex items-center gap-3">
              <span className="h-2 w-2 rounded-full bg-secondary" />
              <div>
                <p className="text-sm text-primary">{str(t["label"]) ? label : titleCase(label)}</p>
                {actor && <p className="text-xs text-muted">{titleCase(actor)}</p>}
              </div>
            </div>
            <span className="text-xs text-muted">{relativeTime(when)}</span>
          </div>
        );
      })}
    </div>
  );
}

export function PodTab({ detail }: { detail: OrderDetail }) {
  const { getApiToken } = useAdminAuth();
  const pod = detail.proof_of_delivery ?? {};
  const photos = Array.isArray(pod.photos) ? (pod.photos as Array<Record<string, unknown>>) : [];
  const signatures = Array.isArray(pod.signatures)
    ? (pod.signatures as Array<Record<string, unknown>>)
    : [];
  const otps = Array.isArray(pod.otp) ? (pod.otp as Array<Record<string, unknown>>) : [];
  const hasGallery = photos.length + signatures.length + otps.length > 0;

  if (!hasGallery) {
    return (
      <EmptyState
        title="No proof of delivery yet"
        hint="Capture in the driver app / Fleetbase — Admin is read-only."
      />
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted">
          Live from Fleetbase
        </p>
        <PodDownloadAll orderId={detail.order_id} getApiToken={getApiToken} />
      </div>
      <div className="flex flex-wrap gap-3">
        {photos.map((p, i) =>
          typeof p.url === "string" ? (
            <figure key={String(p.id ?? i)} className="space-y-1">
              {/* eslint-disable-next-line @next/next/no-img-element -- Fleetbase proof URL */}
              <img
                src={p.url}
                alt="Delivery photo"
                className="h-32 w-32 rounded-xl border border-primary/10 object-cover"
              />
              <PodDownloadOne
                orderId={detail.order_id}
                getApiToken={getApiToken}
                slug={p.download}
                fallbackName={`photo-${i + 1}.jpg`}
              />
            </figure>
          ) : null
        )}
        {signatures.map((s, i) => {
          const src =
            typeof s.url === "string"
              ? s.url
              : typeof s.signature === "string" && s.signature.startsWith("data:")
                ? s.signature
                : null;
          return src ? (
            <figure key={String(s.id ?? `sig-${i}`)} className="space-y-1">
              {/* eslint-disable-next-line @next/next/no-img-element -- Fleetbase signature */}
              <img
                src={src}
                alt="Recipient signature"
                className="h-32 rounded-xl border border-primary/10 bg-gray-bg object-contain px-4"
              />
              <PodDownloadOne
                orderId={detail.order_id}
                getApiToken={getApiToken}
                slug={s.download}
                fallbackName={`signature-${i + 1}.png`}
              />
            </figure>
          ) : null;
        })}
      </div>
      {otps.length > 0 && (
        <p className="text-xs text-muted">
          OTP / barcode:{" "}
          {otps
            .map((o) => String(o.otp ?? o.code ?? ""))
            .filter(Boolean)
            .join(", ")}
        </p>
      )}
    </div>
  );
}

export function MoneyTab({ detail }: { detail: OrderDetail }) {
  const hasInvoice = Boolean(detail.invoice_number);
  const paymentReceipts = detail.payments.filter((p) => p.receipt_url);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Strip label="Order value" value={money(detail.amount_cents, detail.currency)} />
        <Strip
          label="Payment"
          value={
            <Badge tone={paymentTone(detail.payment_status)}>
              {titleCase(detail.payment_status ?? "unpaid")}
            </Badge>
          }
        />
        <Strip label="Quote" value={money(detail.quote_amount_cents, detail.currency)} />
        <Strip
          label="Invoice"
          value={detail.invoice_number ?? "—"}
          sub={
            hasInvoice
              ? `${titleCase(detail.invoice_status)}${
                  detail.invoice_amount_cents != null
                    ? ` · ${money(detail.invoice_amount_cents, detail.currency)}`
                    : ""
                }`
              : titleCase(detail.invoice_status)
          }
        />
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
          Invoice & receipt
        </p>
        {!hasInvoice ? (
          <EmptyState title="No invoice generated" />
        ) : (
          <div className="space-y-2 rounded-xl border border-primary/10 px-3 py-3">
            <div>
              <p className="font-mono text-sm text-primary">{detail.invoice_number}</p>
              <p className="text-xs text-muted">
                {detail.invoice_amount_cents != null
                  ? money(detail.invoice_amount_cents, detail.currency)
                  : "Amount unavailable"}
              </p>
            </div>
            <OrderMoneyDownloads detail={detail} />
            {!detail.invoice_receipt_url && !detail.invoice_pdf_url ? (
              <p className="text-xs text-muted">
                No Stripe receipt URL — use Invoice PDF or Resend receipt (HTML email).
              </p>
            ) : null}
          </div>
        )}
        <p className="mt-2 text-[11px] text-muted">
          Merchant statements are period billing (AR), not per-order — open merchant finance for
          statements.
        </p>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Payments</p>
        {detail.payments.length === 0 ? (
          <EmptyState title="No payment attempts" />
        ) : (
          <div className="divide-y divide-primary/5 rounded-xl border border-primary/10">
            {detail.payments.map((p) => (
              <div key={p.payment_id} className="flex items-center justify-between gap-2 px-3 py-2">
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <Badge tone={paymentTone(p.status)}>{titleCase(p.status)}</Badge>
                  <span className="text-sm text-primary">{money(p.amount_cents, p.currency)}</span>
                  {p.failure_reason && (
                    <span className="text-xs text-red-600">{p.failure_reason}</span>
                  )}
                  {p.receipt_url ? (
                    <a
                      href={p.receipt_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-secondary hover:underline"
                    >
                      Payment receipt
                    </a>
                  ) : null}
                </div>
                <span className="shrink-0 text-xs text-muted">{relativeTime(p.created_at)}</span>
              </div>
            ))}
          </div>
        )}
        {paymentReceipts.length === 0 && detail.payments.length > 0 ? (
          <p className="mt-2 text-[11px] text-muted">
            No Stripe payment receipts on these attempts.
          </p>
        ) : null}
      </div>
    </div>
  );
}

export function CareSection({
  title,
  rows,
  empty,
}: {
  title: string;
  rows: Record<string, unknown>[];
  empty: string;
}) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">{empty}</p>
      ) : (
        <div className="divide-y divide-primary/5 rounded-xl border border-primary/10">
          {rows.map((r, i) => (
            <div key={i} className="flex items-center justify-between px-3 py-2">
              <span className="text-sm text-primary">
                {titleCase(str(r["type"]) ?? str(r["subject"]) ?? str(r["id"]) ?? "Record")}
              </span>
              <Badge tone={str(r["status"]) === "open" ? "amber" : "slate"}>
                {titleCase(str(r["status"]) ?? "open")}
              </Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function CareTab({ detail }: { detail: OrderDetail }) {
  return (
    <div className="space-y-4">
      <CareSection title="Claims" rows={detail.claims} empty="No claims on this order." />
      <CareSection
        title="Support tickets"
        rows={detail.support_tickets}
        empty="No support tickets."
      />
      <CareSection title="Incidents" rows={detail.incidents} empty="No incidents reported." />
    </div>
  );
}
