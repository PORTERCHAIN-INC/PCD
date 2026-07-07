"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Clock,
  CreditCard,
  FileText,
  MapPin,
  Package,
  Radio,
  Sparkles,
  Truck,
  User,
} from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import {
  formatState,
  PAYMENT_STYLES,
  SLA_STYLES,
  STATE_STYLES,
  type OrderDetail,
} from "@/lib/orders";
import { relativeTime } from "@/lib/crmFormat";
import { Badge, Button, Spinner } from "@/components/crm/primitives";
import Order360EmbeddedMap from "@/components/orders/Order360EmbeddedMap";

type Tab =
  | "overview"
  | "timeline"
  | "live-map"
  | "tracking"
  | "packages"
  | "pickup"
  | "stops"
  | "delivery"
  | "merchant"
  | "customer"
  | "driver"
  | "vehicle"
  | "pricing"
  | "payments"
  | "invoices"
  | "documents"
  | "pod"
  | "claims"
  | "support"
  | "communications"
  | "automation"
  | "api"
  | "audit";

const NAV: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "timeline", label: "Timeline" },
  { id: "live-map", label: "Live Map" },
  { id: "tracking", label: "Tracking" },
  { id: "packages", label: "Packages" },
  { id: "pickup", label: "Pickup" },
  { id: "stops", label: "Stops" },
  { id: "delivery", label: "Delivery" },
  { id: "merchant", label: "Merchant" },
  { id: "customer", label: "Customer" },
  { id: "driver", label: "Driver" },
  { id: "vehicle", label: "Vehicle" },
  { id: "pricing", label: "Pricing" },
  { id: "payments", label: "Payments" },
  { id: "invoices", label: "Invoices" },
  { id: "documents", label: "Documents" },
  { id: "pod", label: "Proof Of Delivery" },
  { id: "claims", label: "Claims" },
  { id: "support", label: "Support" },
  { id: "communications", label: "Communications" },
  { id: "automation", label: "Automation" },
  { id: "api", label: "API Activity" },
  { id: "audit", label: "Audit Log" },
];

export type Order360Actions = {
  onAssignDriver: () => void;
  onReassignDriver: () => void;
  onCancel: () => void;
  onDuplicate: () => void;
  onRebook: () => void;
  onCreateReturn: () => void;
  onGenerateInvoice: () => void;
  onRefund: () => void;
  onOpenClaim: () => void;
  onOpenSupport: () => void;
  onShareTracking: () => void;
  onPrintLabels: () => void;
  onPrintManifest: () => void;
};

type Props = {
  detail: OrderDetail | null;
  tracking: Record<string, unknown> | null;
  loading: boolean;
  error?: string | null;
  liveRefreshing?: boolean;
  actions: Order360Actions;
};

export default function OrderDetailView({
  detail,
  tracking,
  loading,
  error,
  liveRefreshing,
  actions,
}: Props) {
  const [tab, setTab] = useState<Tab>("overview");

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }
  if (!detail) {
    return <p className="py-12 text-center text-muted">{error ?? "Order not found"}</p>;
  }

  const smart = detail.smart;
  const pricing = detail.pricing_breakdown as {
    items?: Array<{ code: string; label: string; amount_cents: number }>;
  } | null;
  const live = (tracking?.live ?? detail.tracking) as Record<string, unknown> | null | undefined;
  const openClaims = detail.claims.filter(
    (c) => !["closed", "rejected", "archived"].includes(String(c.status))
  );
  const openTickets = detail.support_tickets.filter(
    (t) => !["closed", "resolved"].includes(String(t.status))
  );
  const driverId = detail.driver_id ?? (detail.driver as Record<string, unknown> | null)?.id;

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col">
      {/* Sticky header */}
      <header className="sticky top-0 z-30 border-b border-primary/10 bg-white/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-white/80">
        <div className="px-4 py-4 lg:px-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <Link
                href="/orders"
                className="mb-2 inline-flex items-center gap-1 text-sm text-muted hover:text-secondary"
              >
                <ArrowLeft className="h-4 w-4" /> Orders
              </Link>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="font-mono text-2xl font-bold text-primary">{detail.order_number}</h1>
                <span
                  className={cn(
                    "rounded-full px-2.5 py-0.5 text-xs font-bold",
                    STATE_STYLES[detail.state] ?? "bg-gray-100"
                  )}
                >
                  {formatState(detail.state)}
                </span>
                <Badge tone={detail.priority === "high" ? "red" : "blue"}>{detail.priority}</Badge>
                {liveRefreshing && (
                  <span className="inline-flex items-center gap-1 text-xs text-green-600">
                    <Radio className="h-3 w-3 animate-pulse" /> Syncing
                  </span>
                )}
              </div>
              <div className="mt-2 grid gap-x-6 gap-y-1 text-xs text-muted sm:grid-cols-2 lg:grid-cols-4">
                <Meta label="Tracking" value={detail.tracking_number} mono />
                <Meta label="Booking #" value={detail.booking_number || "—"} mono />
                <Meta label="Draft #" value={detail.booking_draft_number || "—"} mono />
                <Meta label="Fleetbase ID" value={detail.fleetbase_order_id || "—"} mono />
                <Meta label="Driver" value={detail.driver_name || "Unassigned"} />
                <Meta label="Vehicle" value={detail.vehicle_label || "—"} />
                <Meta label="Merchant" value={detail.merchant_name || "—"} />
                <Meta label="Customer" value={detail.customer_email || "—"} />
                <Meta label="ETA" value={detail.eta ? relativeTime(detail.eta) : "—"} />
                <Meta label="Created" value={relativeTime(detail.created_at)} />
                <Meta label="Updated" value={relativeTime(detail.updated_at)} />
              </div>
            </div>
            <QuickActions detail={detail} actions={actions} />
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6 xl:grid-cols-12">
            <SummaryCard
              label="Payment"
              value={detail.payment_status || "—"}
              tone={detail.payment_status === "SUCCEEDED" ? "green" : "amber"}
            />
            <SummaryCard label="Invoice" value={detail.invoice_status} tone="blue" />
            <SummaryCard
              label="Driver"
              value={detail.driver_status || (detail.driver_name ? "assigned" : "—")}
            />
            <SummaryCard label="Vehicle" value={detail.vehicle_status || "—"} />
            <SummaryCard
              label="ETA"
              value={detail.eta ? relativeTime(detail.eta) : "—"}
              icon={<Clock className="h-3.5 w-3.5" />}
            />
            <SummaryCard
              label="SLA"
              value={detail.sla_status}
              className={SLA_STYLES[detail.sla_status]}
            />
            <SummaryCard
              label="Location"
              value={
                live?.current_location
                  ? "GPS live"
                  : detail.state.includes("TRANSIT")
                    ? "In transit"
                    : "—"
              }
              icon={<MapPin className="h-3.5 w-3.5" />}
            />
            <SummaryCard
              label="Parcels"
              value={String(detail.parcel_count ?? (detail.packages.length || 1))}
              icon={<Package className="h-3.5 w-3.5" />}
            />
            <SummaryCard
              label="Weight"
              value={detail.weight_kg != null ? `${detail.weight_kg} kg` : "—"}
            />
            <SummaryCard
              label="Distance"
              value={
                detail.distance_meters ? `${(detail.distance_meters / 1000).toFixed(1)} km` : "—"
              }
            />
            <SummaryCard
              label="Revenue"
              value={formatCents(detail.amount_cents)}
              icon={<CreditCard className="h-3.5 w-3.5" />}
            />
          </div>

          {smart.ai_summary ? (
            <div className="mt-3 rounded-xl border border-secondary/20 bg-secondary/5 px-3 py-2 text-sm">
              <p className="flex items-center gap-2 text-xs font-bold uppercase text-secondary">
                <Sparkles className="h-3.5 w-3.5" /> Executive summary
              </p>
              <p className="mt-1 text-primary">{String(smart.ai_summary)}</p>
            </div>
          ) : null}
        </div>
      </header>

      <div className="flex flex-1 flex-col lg:flex-row">
        {/* Left navigation */}
        <nav className="shrink-0 border-b border-primary/10 bg-gray-bg/50 lg:w-52 lg:border-b-0 lg:border-r">
          <div className="flex gap-1 overflow-x-auto p-2 lg:flex-col lg:overflow-visible lg:p-3">
            {NAV.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={cn(
                  "shrink-0 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors lg:w-full",
                  tab === t.id
                    ? "bg-white text-secondary shadow-sm ring-1 ring-primary/10"
                    : "text-muted hover:bg-white/60 hover:text-primary"
                )}
              >
                {t.label}
              </button>
            ))}
          </div>
        </nav>

        {/* Main workspace */}
        <main className="min-w-0 flex-1 p-4 lg:p-6">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-primary/10 bg-white p-5 lg:p-6"
          >
            {tab === "overview" && <OverviewTab detail={detail} live={live} />}
            {tab === "timeline" && <TimelineTab detail={detail} />}
            {tab === "live-map" && (
              <Order360EmbeddedMap
                orderId={detail.order_id}
                driverId={driverId ? String(driverId) : null}
                merchantId={detail.merchant_id ?? null}
              />
            )}
            {tab === "tracking" && <TrackingTab detail={detail} tracking={tracking} live={live} />}
            {tab === "packages" && <PackagesTab detail={detail} />}
            {tab === "pickup" && <AddressTab title="Pickup" addr={detail.pickup_detail} />}
            {tab === "stops" && <StopsTab stops={detail.additional_stops} />}
            {tab === "delivery" && <AddressTab title="Delivery" addr={detail.dropoff_detail} />}
            {tab === "merchant" && <Merchant360Tab detail={detail} />}
            {tab === "customer" && <Customer360Tab detail={detail} />}
            {tab === "driver" && <Driver360Tab detail={detail} />}
            {tab === "vehicle" && <Vehicle360Tab detail={detail} />}
            {tab === "pricing" && (
              <PricingTab
                items={pricing?.items}
                total={detail.quote_amount_cents ?? detail.amount_cents}
              />
            )}
            {tab === "payments" && <PaymentsTab detail={detail} />}
            {tab === "invoices" && <InvoicesTab detail={detail} />}
            {tab === "documents" && <DocumentsTab detail={detail} />}
            {tab === "pod" && <PodTab pod={detail.proof_of_delivery} />}
            {tab === "claims" && <ClaimsTab claims={detail.claims} />}
            {tab === "support" && <SupportTab tickets={detail.support_tickets} />}
            {tab === "communications" && (
              <EventListTab items={detail.communications ?? []} empty="No communications logged" />
            )}
            {tab === "automation" && (
              <EventListTab items={detail.automation ?? []} empty="No automation events" />
            )}
            {tab === "api" && <ApiActivityTab detail={detail} />}
            {tab === "audit" && <AuditTab detail={detail} />}
          </motion.div>
        </main>

        {/* Right sidebar */}
        <aside className="hidden shrink-0 border-l border-primary/10 bg-gray-bg/30 xl:block xl:w-72">
          <div className="sticky top-[var(--order360-header,12rem)] space-y-4 p-4">
            <SidebarSection title="Live status">
              <SidebarRow label="Status" value={formatState(detail.state)} />
              <SidebarRow label="ETA" value={detail.eta ? relativeTime(detail.eta) : "—"} />
              <SidebarRow label="Priority" value={detail.priority} />
            </SidebarSection>
            <SidebarSection title="Assignment">
              <SidebarRow label="Driver" value={detail.driver_name || "Unassigned"} />
              <SidebarRow label="Vehicle" value={detail.vehicle_label || "—"} />
            </SidebarSection>
            <SidebarSection title="Parties">
              <SidebarRow label="Customer" value={detail.customer_email || "—"} />
              <SidebarRow label="Merchant" value={detail.merchant_name || "—"} />
            </SidebarSection>
            <SidebarSection title="Payment">
              <SidebarRow label="Status" value={detail.payment_status || "—"} />
              <SidebarRow label="Amount" value={formatCents(detail.amount_cents)} />
            </SidebarSection>
            <SidebarSection title="Open items">
              <SidebarRow label="Tickets" value={String(openTickets.length)} />
              <SidebarRow label="Claims" value={String(openClaims.length)} />
            </SidebarSection>
            {openClaims.length > 0 && (
              <div className="rounded-xl border border-primary/10 bg-white p-3 text-xs">
                {openClaims.slice(0, 3).map((c) => (
                  <Link
                    key={String(c.id)}
                    href={`/claims/${c.id}`}
                    className="block py-1 text-secondary hover:underline"
                  >
                    {String(c.claim_type)}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <p>
      <span className="text-muted">{label}: </span>
      <span className={cn("text-primary", mono && "font-mono")}>{value}</span>
    </p>
  );
}

function SummaryCard({
  label,
  value,
  tone,
  className,
  icon,
}: {
  label: string;
  value: string;
  tone?: "green" | "amber" | "blue";
  className?: string;
  icon?: React.ReactNode;
}) {
  const toneClass =
    className ??
    (tone === "green"
      ? "bg-green-50 text-green-800"
      : tone === "amber"
        ? "bg-amber-50 text-amber-800"
        : tone === "blue"
          ? "bg-blue-50 text-blue-800"
          : "bg-white text-primary");
  return (
    <div className={cn("rounded-xl border border-primary/10 px-3 py-2", toneClass)}>
      <p className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide opacity-70">
        {icon}
        {label}
      </p>
      <p className="mt-0.5 truncate text-sm font-semibold capitalize">{value}</p>
    </div>
  );
}

function QuickActions({ detail, actions }: { detail: OrderDetail; actions: Order360Actions }) {
  const merchant = detail.merchant as Record<string, unknown> | null | undefined;
  const merchantEmail = merchant?.email ? String(merchant.email) : null;
  const merchantPhone = merchant?.phone ? String(merchant.phone) : null;

  const items: Array<{ label: string; onClick?: () => void; href?: string }> = [
    { label: "Assign driver", onClick: actions.onAssignDriver },
    { label: "Reassign driver", onClick: actions.onReassignDriver },
    { label: "Cancel order", onClick: actions.onCancel },
    { label: "Duplicate order", onClick: actions.onDuplicate },
    { label: "Rebook", onClick: actions.onRebook },
    { label: "Create return", onClick: actions.onCreateReturn },
    { label: "Generate invoice", onClick: actions.onGenerateInvoice },
    { label: "Refund", onClick: actions.onRefund },
    { label: "Open claim", onClick: actions.onOpenClaim },
    { label: "Open support ticket", onClick: actions.onOpenSupport },
    { label: "Share tracking", onClick: actions.onShareTracking },
    {
      label: "Email customer",
      href: detail.customer_email ? `mailto:${detail.customer_email}` : undefined,
    },
    {
      label: "Call customer",
      href: detail.customer_phone ? `tel:${detail.customer_phone}` : undefined,
    },
    { label: "Email merchant", href: merchantEmail ? `mailto:${merchantEmail}` : undefined },
    { label: "Call merchant", href: merchantPhone ? `tel:${merchantPhone}` : undefined },
    { label: "Print labels", onClick: actions.onPrintLabels },
    { label: "Print manifest", onClick: actions.onPrintManifest },
  ];

  return (
    <div className="flex max-w-full flex-wrap gap-1.5">
      {items.map((item) =>
        item.href ? (
          <a key={item.label} href={item.href}>
            <Button variant="outline" className="px-2 py-1 text-xs">
              {item.label}
            </Button>
          </a>
        ) : (
          <Button
            key={item.label}
            variant="outline"
            className="px-2 py-1 text-xs"
            onClick={item.onClick}
          >
            {item.label}
          </Button>
        )
      )}
    </div>
  );
}

function SidebarSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-primary/10 bg-white p-3">
      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">{title}</p>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function SidebarRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2 text-xs">
      <span className="text-muted">{label}</span>
      <span className="text-right font-medium text-primary">{value}</span>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4 border-b border-primary/5 py-2 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className={cn("text-right text-primary", mono && "font-mono text-xs break-all")}>
        {value}
      </span>
    </div>
  );
}

function OverviewTab({
  detail,
  live,
}: {
  detail: OrderDetail;
  live?: Record<string, unknown> | null;
}) {
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 font-semibold text-primary">Shipment</h3>
          <Row label="Service" value={detail.service_type || detail.vehicle_class || "—"} />
          <Row label="Pickup" value={detail.pickup} />
          <Row label="Destination" value={detail.destination} />
          <Row label="Special instructions" value={detail.special_instructions || "—"} />
        </div>
        <div>
          <h3 className="mb-3 font-semibold text-primary">Financial</h3>
          <Row
            label="Quote"
            value={detail.quote_amount_cents ? formatCents(detail.quote_amount_cents) : "—"}
          />
          <Row label="Order amount" value={formatCents(detail.amount_cents)} />
          <Row label="Payment" value={detail.payment_status || "—"} />
          <Row label="Invoice" value={detail.invoice_number || "Not generated"} mono />
        </div>
      </div>
      {live && Object.keys(live).length > 0 && (
        <div>
          <h3 className="mb-3 font-semibold text-primary">Live execution</h3>
          <div className="rounded-xl bg-gray-bg p-3 text-xs">
            {live.driver_location ? (
              <Row label="Driver GPS" value={JSON.stringify(live.driver_location)} mono />
            ) : null}
            {live.eta ? <Row label="ETA" value={String(live.eta)} /> : null}
            {live.speed_kmh != null ? <Row label="Speed" value={`${live.speed_kmh} km/h`} /> : null}
          </div>
        </div>
      )}
      {(detail.duplicates as unknown[]).length > 0 && (
        <p className="text-sm text-amber-700">
          {(detail.duplicates as unknown[]).length} possible duplicate order(s) detected.
        </p>
      )}
    </div>
  );
}

function TimelineTab({ detail }: { detail: OrderDetail }) {
  const items = [...detail.timeline];
  return (
    <ol className="relative border-l-2 border-secondary/20 pl-6">
      {items.map((e, i) => (
        <li key={i} className="relative mb-4">
          <span className="absolute -left-[25px] mt-1 h-3 w-3 rounded-full bg-secondary" />
          <p className="font-semibold text-primary">{String(e.label || e.event_type)}</p>
          {e.to_state ? (
            <p className="text-xs text-muted">
              {String(e.from_state)} → {String(e.to_state)}
            </p>
          ) : null}
          <p className="text-xs text-muted">
            {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
          </p>
        </li>
      ))}
      {!items.length && <p className="text-sm text-muted">No timeline events</p>}
    </ol>
  );
}

function TrackingTab({
  detail,
  tracking,
  live,
}: {
  detail: OrderDetail;
  tracking: Record<string, unknown> | null;
  live?: Record<string, unknown> | null;
}) {
  const history = (tracking?.history ?? []) as Array<Record<string, unknown>>;
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 font-semibold">Current position</h3>
        <Row label="State" value={formatState(detail.state)} />
        <Row
          label="Scheduled"
          value={detail.scheduled_at ? String(detail.scheduled_at).slice(0, 16) : "—"}
        />
        {live?.driver_location ? (
          <Row label="GPS" value={JSON.stringify(live.driver_location)} mono />
        ) : (
          <p className="text-sm text-muted">
            Live GPS syncs via Fleetbase when order is in flight.
          </p>
        )}
      </div>
      {history.length > 0 && (
        <div>
          <h3 className="mb-2 font-semibold">GPS history & route</h3>
          <ol className="space-y-2">
            {history.map((h, i) => (
              <li key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-xs">
                <span className="font-medium">{String(h.event_type || h.to_state)}</span>
                <span className="ml-2 text-muted">
                  {h.occurred_at ? relativeTime(String(h.occurred_at)) : ""}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function StopsTab({ stops }: { stops: unknown[] }) {
  if (!stops.length) return <p className="text-sm text-muted">No intermediate stops</p>;
  return (
    <div className="space-y-4">
      {stops.map((stop, i) => (
        <div key={i} className="rounded-xl border border-primary/10 p-3">
          <p className="mb-2 text-xs font-bold text-muted">Stop {i + 1}</p>
          {typeof stop === "object" && stop !== null ? (
            Object.entries(stop as Record<string, unknown>).map(([k, v]) => (
              <Row key={k} label={k.replace(/_/g, " ")} value={v == null ? "—" : String(v)} />
            ))
          ) : (
            <Row label="Address" value={String(stop)} />
          )}
        </div>
      ))}
    </div>
  );
}

function Merchant360Tab({ detail }: { detail: OrderDetail }) {
  const m = detail.merchant;
  if (!m) return <p className="text-sm text-muted">No merchant linked</p>;
  return (
    <div className="space-y-4">
      <EntityRows data={m} />
      <div className="flex gap-2">
        {m.id ? (
          <Link href={`/merchants/${String(m.id)}`}>
            <Button variant="outline" className="px-2 py-1 text-xs">
              <User className="h-4 w-4" /> Merchant profile
            </Button>
          </Link>
        ) : null}
      </div>
    </div>
  );
}

function Customer360Tab({ detail }: { detail: OrderDetail }) {
  const c360 = detail.customer_360;
  return (
    <div className="space-y-4">
      <Row label="Email" value={detail.customer_email || "—"} />
      <Row label="Phone" value={detail.customer_phone || "—"} />
      {c360 ? (
        <>
          <Row label="Lifetime orders" value={String(c360.lifetime_orders ?? "—")} />
          <Row
            label="Lifetime revenue"
            value={
              c360.lifetime_revenue_cents != null
                ? formatCents(Number(c360.lifetime_revenue_cents))
                : "—"
            }
          />
          {(c360.recent_orders as Array<Record<string, unknown>> | undefined)?.length ? (
            <div>
              <p className="mb-2 text-sm font-semibold">Recent orders</p>
              <ul className="space-y-1">
                {(c360.recent_orders as Array<Record<string, unknown>>).map((o) => (
                  <li key={String(o.order_id)}>
                    <Link
                      href={`/orders/${o.order_id}`}
                      className="text-sm text-secondary hover:underline"
                    >
                      {String(o.order_number)} — {formatState(String(o.state))}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function Driver360Tab({ detail }: { detail: OrderDetail }) {
  const d = detail.driver;
  if (!d) return <p className="text-sm text-muted">No driver assigned</p>;
  return (
    <div className="space-y-4">
      <EntityRows data={d} />
      {d.id ? (
        <Link href={`/drivers/${String(d.id)}`}>
          <Button variant="outline" className="px-2 py-1 text-xs">
            <Truck className="h-4 w-4" /> Driver profile
          </Button>
        </Link>
      ) : null}
    </div>
  );
}

function Vehicle360Tab({ detail }: { detail: OrderDetail }) {
  const v = detail.vehicle;
  if (!v) return <p className="text-sm text-muted">No vehicle assigned</p>;
  return <EntityRows data={v} />;
}

function EntityRows({ data }: { data: Record<string, unknown> }) {
  return (
    <>
      {Object.entries(data).map(([k, val]) => {
        if (k === "recent_orders") return null;
        return (
          <Row
            key={k}
            label={k.replace(/_/g, " ")}
            value={val == null ? "—" : typeof val === "object" ? JSON.stringify(val) : String(val)}
          />
        );
      })}
    </>
  );
}

function AddressTab({ title, addr }: { title: string; addr: Record<string, unknown> }) {
  if (!addr || !Object.keys(addr).length)
    return <p className="text-sm text-muted">No {title.toLowerCase()} address on file</p>;
  return (
    <>
      <h3 className="mb-3 font-semibold">{title}</h3>
      {Object.entries(addr).map(([k, v]) => (
        <Row key={k} label={k.replace(/_/g, " ")} value={String(v ?? "—")} />
      ))}
    </>
  );
}

function PackagesTab({ detail }: { detail: OrderDetail }) {
  return (
    <div className="space-y-4">
      {detail.packages.map((p, i) => (
        <div key={i} className="rounded-xl border border-primary/10 p-3 text-sm">
          <p className="mb-2 text-xs font-bold text-muted">Parcel {i + 1}</p>
          {Object.entries(p).map(([k, v]) => (
            <Row key={k} label={k.replace(/_/g, " ")} value={v == null ? "—" : String(v)} />
          ))}
        </div>
      ))}
      {!detail.packages.length && (
        <>
          <Row label="Type" value={detail.package_type || "—"} />
          <Row label="Weight" value={detail.weight_kg != null ? `${detail.weight_kg} kg` : "—"} />
          <Row label="Dimensions" value={detail.dimensions || "—"} />
          <Row
            label="Declared value"
            value={detail.declared_value_cents ? formatCents(detail.declared_value_cents) : "—"}
          />
        </>
      )}
    </div>
  );
}

function PricingTab({
  items,
  total,
}: {
  items?: Array<{ code: string; label: string; amount_cents: number }>;
  total: number;
}) {
  if (!items?.length) return <p className="text-sm text-muted">No pricing breakdown stored</p>;
  return (
    <div className="space-y-2">
      {items.map((line) => (
        <div key={line.code} className="flex justify-between text-sm">
          <span className="text-muted">{line.label}</span>
          <span className="font-medium">{formatCents(line.amount_cents)}</span>
        </div>
      ))}
      <div className="flex justify-between border-t border-primary/10 pt-2 font-bold">
        <span>Final amount</span>
        <span>{formatCents(total)}</span>
      </div>
    </div>
  );
}

function PaymentsTab({ detail }: { detail: OrderDetail }) {
  return (
    <div className="space-y-3">
      {detail.payments.map((p) => (
        <div key={p.payment_id} className="rounded-xl border border-primary/10 p-3 text-sm">
          <div className="mb-1 flex justify-between">
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-bold",
                PAYMENT_STYLES[p.status] ?? "bg-gray-100"
              )}
            >
              {p.status}
            </span>
            <span className="font-semibold">{formatCents(p.amount_cents)}</span>
          </div>
          {p.stripe_payment_intent_id && (
            <Row label="Payment intent" value={p.stripe_payment_intent_id} mono />
          )}
          {p.stripe_checkout_session_id && (
            <Row label="Checkout session" value={p.stripe_checkout_session_id} mono />
          )}
          {p.receipt_url && (
            <a
              href={p.receipt_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-secondary hover:underline"
            >
              Receipt
            </a>
          )}
        </div>
      ))}
      {!detail.payments.length && <p className="text-sm text-muted">No payments recorded</p>}
    </div>
  );
}

function InvoicesTab({ detail }: { detail: OrderDetail }) {
  if (!detail.invoice_number) return <p className="text-sm text-muted">No invoice generated</p>;
  return (
    <>
      <Row label="Invoice #" value={detail.invoice_number} mono />
      <Row
        label="Amount"
        value={detail.invoice_amount_cents ? formatCents(detail.invoice_amount_cents) : "—"}
      />
      <div className="mt-3 flex gap-3">
        {detail.invoice_receipt_url && (
          <a
            href={detail.invoice_receipt_url}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-secondary hover:underline"
          >
            Receipt
          </a>
        )}
        {detail.invoice_pdf_url && (
          <a
            href={detail.invoice_pdf_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-sm text-secondary hover:underline"
          >
            <FileText className="h-4 w-4" /> Download PDF
          </a>
        )}
      </div>
    </>
  );
}

function DocumentsTab({ detail }: { detail: OrderDetail }) {
  return (
    <ul className="space-y-2">
      {detail.documents.map((d, i) => (
        <li key={i}>
          <a
            href={String(d.url)}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-secondary hover:underline"
          >
            {String(d.name)} ({String(d.type)})
          </a>
        </li>
      ))}
      {!detail.documents.length && <p className="text-sm text-muted">No documents</p>}
    </ul>
  );
}

function PodTab({ pod }: { pod: Record<string, unknown> }) {
  if (!Object.keys(pod).length)
    return <p className="text-sm text-muted">Proof of delivery not yet captured</p>;
  return (
    <div className="space-y-2">
      {Object.entries(pod).map(([k, v]) => (
        <Row
          key={k}
          label={k.replace(/_/g, " ")}
          value={typeof v === "object" ? JSON.stringify(v) : String(v ?? "—")}
          mono={typeof v === "object"}
        />
      ))}
    </div>
  );
}

function ClaimsTab({ claims }: { claims: Array<Record<string, unknown>> }) {
  return (
    <ul className="space-y-2">
      {claims.map((c) => (
        <li key={String(c.id)} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          <Link href={`/claims/${c.id}`} className="font-medium text-secondary hover:underline">
            {String(c.claim_type)} — {String(c.status)}
          </Link>
          {c.description ? (
            <p className="mt-1 text-xs text-muted">{String(c.description)}</p>
          ) : null}
        </li>
      ))}
      {!claims.length && <p className="text-sm text-muted">No claims on this order</p>}
    </ul>
  );
}

function SupportTab({ tickets }: { tickets: Array<Record<string, unknown>> }) {
  return (
    <ul className="space-y-2">
      {tickets.map((t) => (
        <li key={String(t.id)} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          <Link href={`/support/${t.id}`} className="font-medium text-secondary hover:underline">
            {String(t.subject || t.id)}
          </Link>
          <span className="ml-2 text-xs text-muted">{String(t.status || "")}</span>
        </li>
      ))}
      {!tickets.length && <p className="text-sm text-muted">No support tickets</p>}
    </ul>
  );
}

function EventListTab({ items, empty }: { items: Array<Record<string, unknown>>; empty: string }) {
  return (
    <div className="space-y-2">
      {items.map((e, i) => (
        <div key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          <p className="font-medium">{String(e.label || e.event_type)}</p>
          <p className="text-xs text-muted">
            {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
            {e.source ? ` · ${String(e.source)}` : ""}
          </p>
        </div>
      ))}
      {!items.length && <p className="text-sm text-muted">{empty}</p>}
    </div>
  );
}

function ApiActivityTab({ detail }: { detail: OrderDetail }) {
  const items = [
    ...(detail.api_activity ?? []),
    ...detail.domain_events.filter((e) =>
      String(e.event_type).match(/stripe|fleetbase|firebase|webhook|email|maps/i)
    ),
  ];
  return <EventListTab items={items} empty="No API activity recorded" />;
}

function AuditTab({ detail }: { detail: OrderDetail }) {
  return (
    <div className="space-y-2">
      {detail.audit_log.map((a, i) => (
        <div key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          <p className="font-medium">{String(a.action)}</p>
          <p className="text-xs text-muted">
            {a.created_at ? relativeTime(String(a.created_at)) : ""}
            {a.actor_user_id ? ` · ${String(a.actor_user_id)}` : ""}
          </p>
          {a.payload &&
          typeof a.payload === "object" &&
          Object.keys(a.payload as object).length > 0 ? (
            <pre className="mt-1 overflow-auto rounded bg-gray-bg p-2 text-[10px]">
              {JSON.stringify(a.payload, null, 2)}
            </pre>
          ) : null}
        </div>
      ))}
      {!detail.audit_log.length && <p className="text-sm text-muted">No audit entries</p>}
    </div>
  );
}
