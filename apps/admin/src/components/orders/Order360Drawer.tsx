"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Circle,
  CircleDot,
  ClipboardList,
  Copy,
  ExternalLink,
  FileCheck2,
  History,
  LifeBuoy,
  Sparkles,
  Wallet,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { ops, SLA_TONE } from "@/lib/operations";
import { orderSourceLabel, ordersApi, shopifyAdminUrl, type OrderDetail } from "@/lib/orders";
import { dateTime, money, relativeTime, titleCase } from "@/lib/crmFormat";
import { Badge, Button, Drawer, EmptyState, Spinner } from "@/components/crm/primitives";
import { OrderRouteMap } from "@/components/orders/OrderRouteMap";
import { AssignDriverModal } from "@/components/orders/AssignDriverModal";
import {
  ExceptionReasonModal,
  type ExceptionColumn,
} from "@/components/orders/ExceptionReasonModal";
import { OrderAssistPanel } from "@/components/orders/OrderAssistPanel";
import { PodDownloadAll, PodDownloadOne } from "@/components/orders/PodDownloads";
import { ActionFlash, OrderMoneyDownloads } from "@/components/orders/sections";
// Order-level progress rank — per-stop execution truth lives in Fleetbase and
// arrives via detail.tracking waypoints when the driver app reports it.
const STATE_RANK: Record<string, number> = {
  BOOKED: 0,
  DISPATCH_READY: 1,
  DRIVER_ASSIGNED: 2,
  DRIVER_ACCEPTED: 3,
  DRIVER_EN_ROUTE: 4,
  AT_PICKUP: 5,
  PICKED_UP: 6,
  IN_TRANSIT: 7,
  AT_DESTINATION: 8,
  DELIVERED: 9,
  POD_COMPLETED: 10,
  INVOICED: 11,
  CLOSED: 12,
  CANCELLED: 0,
  REFUNDED: 0,
  FAILED: 6,
  RETURN_TO_SENDER: 6,
  DAMAGED: 6,
  LOST: 6,
  CLAIM_OPEN: 6,
};

const WAYPOINT_DONE = new Set(["completed", "delivered", "picked_up", "done"]);

const str = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v : null);

function addressOf(rec: Record<string, unknown> | null | undefined): string {
  if (!rec) return "—";
  for (const k of ["formatted_address", "formatted", "address", "street1", "city", "name"]) {
    const v = str(rec[k]);
    if (v) return v;
  }
  return "—";
}

function trackingWaypointStatuses(tracking: Record<string, unknown> | null | undefined): string[] {
  if (!tracking) return [];
  const direct = tracking["waypoints"];
  const nested = (tracking["payload"] as Record<string, unknown> | undefined)?.["waypoints"];
  const wp = Array.isArray(direct) ? direct : Array.isArray(nested) ? nested : [];
  return wp.map((w) => {
    const r = (w ?? {}) as Record<string, unknown>;
    return (str(r["status"]) ?? str(r["status_code"]) ?? "").toLowerCase();
  });
}

type StopView = {
  key: string;
  label: string;
  address: string;
  state: "done" | "current" | "pending";
};

function buildStops(detail: OrderDetail): StopView[] {
  const rank = STATE_RANK[detail.state] ?? 0;
  const mids = (detail.additional_stops ?? []).map((s) => (s ?? {}) as Record<string, unknown>);
  const wp = trackingWaypointStatuses(detail.tracking);
  const stops: StopView[] = [
    {
      key: "pickup",
      label: "Pickup",
      address: addressOf(detail.pickup_detail),
      state: rank >= 6 ? "done" : rank >= 4 ? "current" : "pending",
    },
    ...mids.map((m, i): StopView => ({
      key: `stop-${i}`,
      label: `Stop ${i + 1}`,
      address: addressOf(m),
      state: rank >= 9 || WAYPOINT_DONE.has(wp[i] ?? "") ? "done" : "pending",
    })),
    {
      key: "dropoff",
      label: "Delivery",
      address: addressOf(detail.dropoff_detail),
      state: rank >= 9 ? "done" : rank === 8 ? "current" : "pending",
    },
  ];
  // IN_TRANSIT and similar states don't pin a leg — flag the first pending stop.
  if (rank >= 6 && rank < 9 && !stops.some((s) => s.state === "current")) {
    const next = stops.find((s) => s.state === "pending");
    if (next) next.state = "current";
  }
  return stops;
}

function paymentTone(s: string | null | undefined): string {
  if (s === "SUCCEEDED") return "green";
  if (s === "FAILED") return "red";
  return s ? "amber" : "slate";
}

function SlaBadge({ sla }: { sla: string }) {
  return (
    <Badge tone={SLA_TONE[sla] ?? "slate"}>{sla === "at_risk" ? "At risk" : titleCase(sla)}</Badge>
  );
}

function Strip({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="rounded-xl border border-primary/10 bg-white p-3">
      <p className="text-[11px] font-medium text-muted">{label}</p>
      <div className="mt-1 text-sm font-semibold text-primary">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-muted">{sub}</div>}
    </div>
  );
}

function RouteTimeline({ detail }: { detail: OrderDetail }) {
  const stops = buildStops(detail);
  return (
    <div className="rounded-2xl border border-primary/10 bg-white">
      <div className="flex items-center justify-between border-b border-primary/10 px-4 py-3">
        <p className="text-sm font-semibold text-primary">
          Route · {stops.length} stop{stops.length === 1 ? "" : "s"}
        </p>
        <span className="text-[11px] text-muted">Per-stop status syncs from Fleetbase</span>
      </div>
      <div className="px-4 py-4">
        {stops.map((s, i) => (
          <div key={s.key} className="relative flex gap-3 pb-4 last:pb-0">
            {i < stops.length - 1 && (
              <span className="absolute left-[9px] top-6 h-[calc(100%-1.25rem)] w-0.5 bg-primary/10" />
            )}
            <span className="z-10 mt-0.5 shrink-0 bg-white">
              {s.state === "done" ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : s.state === "current" ? (
                <CircleDot className="h-5 w-5 text-secondary" />
              ) : (
                <Circle className="h-5 w-5 text-primary/25" />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
                {s.label}
                {s.state === "current" && <Badge tone="blue">In progress</Badge>}
              </p>
              <p
                className={cn(
                  "truncate text-sm",
                  s.state === "pending" ? "text-muted" : "text-primary"
                )}
              >
                {s.address}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

type DrawerTab = "overview" | "assist" | "journey" | "evidence" | "money" | "care";
const DRAWER_TABS: {
  id: DrawerTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { id: "overview", label: "Overview", icon: ClipboardList },
  { id: "journey", label: "Journey", icon: History },
  { id: "assist", label: "Assist", icon: Sparkles },
  { id: "evidence", label: "Evidence", icon: FileCheck2 },
  { id: "money", label: "Money", icon: Wallet },
  { id: "care", label: "Care", icon: LifeBuoy },
];

function pickupWindowFromStops(stops?: Array<Record<string, unknown>> | null): string | null {
  const pickup = (stops || []).find((stop) => {
    const kind = String(stop.stop_type || stop.type || "").toLowerCase();
    return kind === "pickup" || kind === "pick";
  });
  if (!pickup) return null;
  const start = pickup.time_window_start;
  const end = pickup.time_window_end;
  if (!start && !end) return null;
  return `${start ? dateTime(String(start)) : "?"} – ${end ? dateTime(String(end)) : "?"}`;
}

function exceptionColumnFromState(state?: string): ExceptionColumn | "" {
  const s = (state || "").toUpperCase();
  if (s === "FAILED") return "failed";
  if (s === "RETURN_TO_SENDER") return "returned";
  if (s === "LOST") return "lost";
  if (s === "DAMAGED") return "damaged";
  return "";
}

function DetailsTab({ detail }: { detail: OrderDetail }) {
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
          [
            "Shopify admin",
            shopifyAdminUrl(detail.shopify) ? (
              <a
                className="text-secondary hover:underline"
                href={shopifyAdminUrl(detail.shopify) ?? undefined}
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

function TimelineTab({ detail }: { detail: OrderDetail }) {
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

function PodTab({ detail }: { detail: OrderDetail }) {
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

function MoneyTab({ detail }: { detail: OrderDetail }) {
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

function CareSection({
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

function CareTab({ detail }: { detail: OrderDetail }) {
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

type NextAction = {
  key: string;
  label: string;
  hint: string;
  kind: "assign" | "exception" | "operations" | "money" | "none";
};

function nextActionFor(detail: OrderDetail): NextAction {
  const state = detail.state;
  if (["DISPATCH_READY", "BOOKED", "DRIVER_REJECTED"].includes(state)) {
    return {
      key: "assign",
      label: "Assign driver",
      hint: "PC-owned · syncs via permanent bond",
      kind: "assign",
    };
  }
  if (state === "DRIVER_ASSIGNED") {
    return {
      key: "operations",
      label: "Watch on Operations",
      hint: "Accept → pickup → deliver mirrors via Fleetbase bond",
      kind: "operations",
    };
  }
  if (
    [
      "DRIVER_ACCEPTED",
      "DRIVER_EN_ROUTE",
      "AT_PICKUP",
      "PICKED_UP",
      "IN_TRANSIT",
      "AT_DESTINATION",
    ].includes(state)
  ) {
    return {
      key: "operations",
      label: "Open Operations",
      hint: "Live progress mirrors via permanent bond",
      kind: "operations",
    };
  }
  if (state === "POD_COMPLETED" && !detail.invoice_number) {
    return {
      key: "money",
      label: "Generate invoice",
      hint: "POD complete — create invoice + receipt email",
      kind: "money",
    };
  }
  if (["DELIVERED", "POD_COMPLETED", "INVOICED"].includes(state) && detail.invoice_number) {
    return {
      key: "money",
      label: "View money",
      hint: "Invoice on file — resend receipt from full Order 360",
      kind: "money",
    };
  }
  if (["FAILED", "RETURN_TO_SENDER", "LOST", "DAMAGED"].includes(state)) {
    return {
      key: "exception",
      label: "Review exception",
      hint: "Update exception or retry from Exceptions tab",
      kind: "exception",
    };
  }
  return {
    key: "none",
    label: "No action needed",
    hint: titleCase(detail.display_state || detail.state),
    kind: "none",
  };
}

export function Order360Drawer({
  orderId,
  onClose,
  onChanged,
}: {
  orderId: string | null;
  onClose: () => void;
  onChanged?: () => void;
}) {
  const {
    data: detail,
    loading,
    error,
    isFetching,
    getApiToken,
    refetch,
  } = useApiData((t) => ordersApi.detail(t, orderId ?? ""), [orderId], {
    key: "order360-drawer",
    enabled: !!orderId,
  });

  const [tab, setTab] = useState<DrawerTab>("overview");
  const [assignOpen, setAssignOpen] = useState(false);
  const [exceptionOpen, setExceptionOpen] = useState(false);
  const [exceptionInitial, setExceptionInitial] = useState<ExceptionColumn | "">("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function copyTracking() {
    if (!detail) return;
    try {
      await navigator.clipboard.writeText(detail.tracking_number);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setActionError("Could not copy to clipboard");
    }
  }

  const isHigh = detail?.priority?.toLowerCase() === "high";
  const next = detail ? nextActionFor(detail) : null;

  return (
    <>
      <Drawer
        open={!!orderId}
        onClose={onClose}
        width="max-w-2xl"
        title={
          detail ? (
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-mono">{detail.tracking_number}</span>
              <Badge tone="sky">{titleCase(detail.display_state || detail.state)}</Badge>
              <SlaBadge sla={detail.sla_status} />
              {isHigh && <Badge tone="red">High</Badge>}
            </span>
          ) : (
            "Order 360"
          )
        }
        footer={
          detail && (
            <div className="flex w-full flex-wrap items-center gap-2">
              {actionError && (
                <div className="w-full">
                  <ActionFlash error={actionError} />
                </div>
              )}
              <Button
                className="px-3 py-1.5 text-xs"
                onClick={() => setAssignOpen(true)}
                disabled={[
                  "DELIVERED",
                  "POD_COMPLETED",
                  "INVOICED",
                  "CLOSED",
                  "CANCELLED",
                ].includes(detail.state)}
              >
                {detail.driver_name ? "Reassign" : "Assign driver"}
              </Button>
              <Button
                variant="danger"
                className="px-3 py-1.5 text-xs"
                onClick={() => {
                  setExceptionInitial("");
                  setExceptionOpen(true);
                }}
              >
                Mark exception
              </Button>
              <div className="ml-auto flex items-center gap-2">
                <Button
                  variant="outline"
                  className="px-3 py-1.5 text-xs"
                  onClick={() => void copyTracking()}
                >
                  {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied ? "Copied" : "Copy tracking"}
                </Button>
                <Link
                  href={`/orders/${detail.order_id}`}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-primary/15 bg-white px-3 py-1.5 text-xs font-medium text-primary hover:bg-gray-bg"
                >
                  Open full page <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          )
        }
      >
        {loading && !detail ? (
          <Spinner label="Loading order…" />
        ) : error && !detail ? (
          <div className="space-y-3 py-6 text-center">
            <p className="text-sm text-red-600">Could not load order: {error}</p>
            <Button variant="outline" onClick={() => void refetch()} disabled={isFetching}>
              {isFetching ? "Retrying…" : "Retry"}
            </Button>
          </div>
        ) : detail ? (
          <div className="space-y-4">
            {/* Primary next action */}
            {next && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-secondary/20 bg-secondary/5 px-4 py-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">
                    Next best action
                  </p>
                  <p className="text-sm font-semibold text-primary">{next.label}</p>
                  <p className="text-xs text-muted">{next.hint}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {next.kind === "assign" && (
                    <Button className="px-3 py-1.5 text-xs" onClick={() => setAssignOpen(true)}>
                      Assign driver
                    </Button>
                  )}
                  {next.kind === "operations" && (
                    <Link href="/operations">
                      <Button variant="outline" className="px-3 py-1.5 text-xs">
                        Open Operations
                      </Button>
                    </Link>
                  )}
                  {next.kind === "money" && (
                    <Button
                      variant="outline"
                      className="px-3 py-1.5 text-xs"
                      onClick={() => setTab("money")}
                    >
                      Open Money
                    </Button>
                  )}
                  {next.kind === "exception" && (
                    <Button
                      variant="danger"
                      className="px-3 py-1.5 text-xs"
                      onClick={() => setExceptionOpen(true)}
                    >
                      Mark exception
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* Situation strip */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <Strip
                label="Driver"
                value={detail.driver_name ?? "Unassigned"}
                sub={detail.driver_status ? titleCase(detail.driver_status) : detail.vehicle_label}
              />
              <Strip
                label="Promised ETA"
                value={detail.eta ? dateTime(detail.eta) : "—"}
                sub={`SLA ${titleCase(detail.sla_status)}`}
              />
              <Strip
                label="Payment"
                value={
                  <Badge tone={paymentTone(detail.payment_status)}>
                    {titleCase(detail.payment_status ?? "unpaid")}
                  </Badge>
                }
              />
              <Strip
                label="Invoice"
                value={detail.invoice_number ?? "—"}
                sub={titleCase(detail.invoice_status)}
              />
              <Strip
                label="PC ↔ FB"
                value={
                  detail.status_sync?.fleetbase_status
                    ? String(detail.status_sync.fleetbase_status)
                    : "—"
                }
                sub={
                  detail.status_sync?.status_aligned === true
                    ? "Aligned"
                    : detail.status_sync?.status_aligned === false
                      ? "Drift"
                      : String(detail.status_sync?.truth ?? "PC only")
                }
              />
            </div>

            <RouteTimeline detail={detail} />

            {detail.order_id && <OrderRouteMap orderId={detail.order_id} />}

            <div className="rounded-2xl border border-primary/10 bg-white">
              <div className="flex gap-1 overflow-x-auto border-b border-primary/10 px-3 pt-3">
                {DRAWER_TABS.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setTab(id)}
                    className={cn(
                      "flex shrink-0 items-center gap-1.5 rounded-t-lg px-3 py-2 text-xs font-medium transition-colors",
                      tab === id ? "bg-gray-bg text-primary" : "text-primary/60 hover:bg-gray-bg/60"
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </button>
                ))}
                {isFetching && (
                  <span className="ml-auto self-center text-[11px] text-muted">Refreshing…</span>
                )}
              </div>
              <div className="px-4 py-4">
                {tab === "overview" && <DetailsTab detail={detail} />}
                {tab === "assist" && orderId && (
                  <OrderAssistPanel
                    orderId={orderId}
                    compact
                    onChanged={() => {
                      void refetch();
                      onChanged?.();
                    }}
                    onOpenAssign={() => setAssignOpen(true)}
                    onOpenException={(suggested) => {
                      setExceptionInitial(exceptionColumnFromState(suggested));
                      setExceptionOpen(true);
                    }}
                  />
                )}
                {tab === "journey" && <TimelineTab detail={detail} />}
                {tab === "evidence" && <PodTab detail={detail} />}
                {tab === "money" && <MoneyTab detail={detail} />}
                {tab === "care" && <CareTab detail={detail} />}
              </div>
            </div>

            {detail.incidents.length > 0 && (
              <p className="flex items-center gap-1.5 text-xs text-amber-700">
                <AlertTriangle className="h-3.5 w-3.5" />
                {detail.incidents.length} open incident(s) — see the Care tab.
              </p>
            )}
          </div>
        ) : null}
      </Drawer>

      <AssignDriverModal
        open={assignOpen}
        orderId={orderId}
        trackingNumber={detail?.tracking_number}
        currentDriverName={detail?.driver_name}
        onClose={() => setAssignOpen(false)}
        onAssigned={() => {
          void refetch();
          onChanged?.();
        }}
      />
      <ExceptionReasonModal
        open={exceptionOpen}
        trackingNumber={detail?.tracking_number}
        initialColumn={exceptionInitial}
        allowColumnChange
        onClose={() => {
          setExceptionOpen(false);
          setExceptionInitial("");
        }}
        onConfirm={async (column, reason) => {
          if (!orderId) return;
          setActionError(null);
          try {
            const token = await getApiToken();
            await ops.moveBoardOrder(token, orderId, column, reason);
            await refetch();
            onChanged?.();
          } catch (e) {
            setActionError(e instanceof Error ? e.message : "Could not mark exception");
            throw e;
          }
        }}
      />
    </>
  );
}
