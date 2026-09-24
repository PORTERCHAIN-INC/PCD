"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Clock,
  CreditCard,
  MapPin,
  Package,
  Radio,
  Sparkles,
  Truck,
  User,
} from "lucide-react";
import { QuoteLines } from "@porterchain/ui/quote-lines";
import { cn, formatCents } from "@porterchain/ui/utils";
import {
  formatState,
  orderSourceLabel,
  ordersApi,
  shopifyAdminUrl,
  PAYMENT_STYLES,
  SLA_STYLES,
  STATE_STYLES,
  type OrderDetail,
} from "@/lib/orders";
import { relativeTime } from "@/lib/crmFormat";
import { Badge, Button, Spinner } from "@/components/crm/primitives";
import { OrderAssistPanel } from "@/components/orders/OrderAssistPanel";
import { PodDownloadAll, PodDownloadOne } from "@/components/orders/PodDownloads";
import { ActionFlash, SectionBlock } from "@/components/orders/sections";
import { OrderMoneyDownloads } from "@/components/orders/sections/OrderMoneyDownloads";
import { useAdminAuth } from "@/hooks/useAdminAuth";

type Section =
  "overview" | "journey" | "parties" | "money" | "evidence" | "care" | "assist" | "system";

const SECTIONS: { id: Section; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "journey", label: "Journey" },
  { id: "parties", label: "Parties" },
  { id: "money", label: "Money" },
  { id: "evidence", label: "Evidence" },
  { id: "care", label: "Care" },
  { id: "assist", label: "Assist" },
  { id: "system", label: "System" },
];

const LEGACY_TAB_TO_SECTION: Record<string, Section> = {
  overview: "overview",
  assist: "assist",
  timeline: "journey",
  tracking: "journey",
  packages: "journey",
  pickup: "journey",
  stops: "journey",
  delivery: "journey",
  merchant: "parties",
  customer: "parties",
  driver: "parties",
  vehicle: "parties",
  pricing: "money",
  payments: "money",
  invoices: "money",
  documents: "evidence",
  pod: "evidence",
  claims: "care",
  support: "care",
  communications: "care",
  automation: "system",
  api: "system",
  audit: "system",
};

function parseSection(value: string | null): Section {
  if (!value) return "overview";
  if (SECTIONS.some((s) => s.id === value)) return value as Section;
  return LEGACY_TAB_TO_SECTION[value] ?? "overview";
}

export type Order360Actions = {
  onAssignDriver: () => void;
  onReassignDriver: () => void;
  /** Optional suggested exception column from assist (failed/returned/lost/damaged). */
  onMarkException: (suggested?: string) => void;
  onCancel: () => void;
  onDuplicate: () => void;
  onRebook: () => void;
  onCreateReturn: () => void;
  onGenerateInvoice: () => void;
  onResendReceipt: () => void;
  onRefund: () => void;
  onOpenClaim: () => void;
  onOpenSupport: () => void;
  onShareTracking: () => void;
  onPrintLabels: () => void;
  onPrintManifest: () => void;
  onDownloadRecord: () => void;
};

type Props = {
  detail: OrderDetail | null;
  tracking: Record<string, unknown> | null;
  loading: boolean;
  error?: string | null;
  liveRefreshing?: boolean;
  actions: Order360Actions;
  actionError?: string | null;
  actionNotice?: string | null;
  onRefresh?: () => void;
};

export default function OrderDetailView({
  detail,
  tracking,
  loading,
  error,
  liveRefreshing,
  actions,
  actionError,
  actionNotice,
  onRefresh,
}: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [section, setSection] = useState<Section>(() =>
    parseSection(searchParams.get("section") ?? searchParams.get("tab"))
  );

  useEffect(() => {
    setSection(parseSection(searchParams.get("section") ?? searchParams.get("tab")));
  }, [searchParams]);

  function goSection(next: Section) {
    setSection(next);
    const params = new URLSearchParams(searchParams.toString());
    params.delete("tab");
    params.set("section", next);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

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
  const live = (tracking?.live ?? detail.tracking) as Record<string, unknown> | null | undefined;
  const openClaims = detail.claims.filter(
    (c) => !["closed", "rejected", "archived"].includes(String(c.status))
  );
  const openTickets = detail.support_tickets.filter(
    (t) => !["closed", "resolved"].includes(String(t.status))
  );

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
                <Meta
                  label="PC ↔ Fleetbase"
                  value={
                    detail.status_sync?.fleetbase_status
                      ? `${String(detail.status_sync.pc_state)} · FB ${String(detail.status_sync.fleetbase_status)}${
                          detail.status_sync.status_aligned === true
                            ? " · aligned"
                            : detail.status_sync.status_aligned === false
                              ? " · drift"
                              : ""
                        }`
                      : String(detail.status_sync?.truth ?? "PC commercial only")
                  }
                />
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
              label="Promised ETA"
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
                  ? "Fleetbase GPS (polled)"
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
              label="Quoted distance"
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

          <ActionFlash error={actionError} notice={actionNotice} className="mt-3" />
        </div>
      </header>

      <div className="flex flex-1 flex-col lg:flex-row">
        {/* Left navigation — horizontal chips on mobile */}
        <nav className="shrink-0 border-b border-primary/10 bg-gray-bg/50 lg:w-52 lg:border-b-0 lg:border-r">
          <div className="flex gap-1 overflow-x-auto p-2 lg:flex-col lg:overflow-visible lg:p-3">
            {SECTIONS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => goSection(t.id)}
                className={cn(
                  "shrink-0 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors lg:w-full",
                  section === t.id
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
            key={section}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-primary/10 bg-white p-5 lg:p-6"
          >
            {section === "overview" && (
              <OverviewTab detail={detail} live={live} onRefresh={onRefresh} />
            )}
            {section === "assist" && (
              <OrderAssistPanel
                orderId={detail.order_id}
                onChanged={onRefresh}
                onOpenAssign={actions.onAssignDriver}
                onOpenException={(suggested) => actions.onMarkException(suggested)}
              />
            )}
            {section === "journey" && (
              <div className="space-y-8">
                <SectionBlock title="Timeline">
                  <TimelineTab detail={detail} />
                </SectionBlock>
                <SectionBlock title="Tracking">
                  <TrackingTab detail={detail} tracking={tracking} live={live} />
                </SectionBlock>
                <SectionBlock title="Packages">
                  <PackagesTab detail={detail} onRefresh={onRefresh} />
                </SectionBlock>
                <SectionBlock title="Pickup">
                  <AddressTab title="Pickup" addr={detail.pickup_detail} />
                </SectionBlock>
                <SectionBlock title="Stops">
                  <StopsTab stops={detail.additional_stops} />
                </SectionBlock>
                <SectionBlock title="Delivery">
                  <AddressTab title="Delivery" addr={detail.dropoff_detail} />
                </SectionBlock>
              </div>
            )}
            {section === "parties" && (
              <div className="space-y-8">
                <SectionBlock title="Merchant">
                  <Merchant360Tab detail={detail} />
                </SectionBlock>
                <SectionBlock title="Customer">
                  <Customer360Tab detail={detail} />
                </SectionBlock>
                <SectionBlock title="Driver">
                  <Driver360Tab detail={detail} />
                </SectionBlock>
                <SectionBlock title="Vehicle">
                  <Vehicle360Tab detail={detail} />
                </SectionBlock>
              </div>
            )}
            {section === "money" && (
              <div className="space-y-8">
                <SectionBlock title="Pricing">
                  <QuoteLines
                    breakdown={detail.pricing_breakdown}
                    quotedCents={detail.quote_amount_cents}
                    chargedCents={detail.amount_cents}
                    currency={(detail.currency || "cad").toUpperCase()}
                  />
                </SectionBlock>
                <SectionBlock title="Payments">
                  <PaymentsTab detail={detail} />
                </SectionBlock>
                <SectionBlock title="Invoices">
                  <InvoicesTab detail={detail} />
                </SectionBlock>
              </div>
            )}
            {section === "evidence" && (
              <div className="space-y-8">
                <SectionBlock title="Proof of delivery">
                  <PodTab pod={detail.proof_of_delivery} orderId={detail.order_id} />
                </SectionBlock>
                <SectionBlock title="Documents">
                  <DocumentsTab detail={detail} onDownloadRecord={actions.onDownloadRecord} />
                </SectionBlock>
              </div>
            )}
            {section === "care" && (
              <div className="space-y-8">
                <SectionBlock title="Claims">
                  <ClaimsTab claims={detail.claims} />
                </SectionBlock>
                <SectionBlock title="Support">
                  <SupportTab tickets={detail.support_tickets} />
                </SectionBlock>
                <SectionBlock title="Communications">
                  <CommunicationsTab items={detail.communications ?? []} />
                </SectionBlock>
              </div>
            )}
            {section === "system" && (
              <div className="space-y-8">
                <SectionBlock title="Automation">
                  <EventListTab items={detail.automation ?? []} empty="No automation events" />
                </SectionBlock>
                <SectionBlock title="API activity">
                  <ApiActivityTab detail={detail} />
                </SectionBlock>
                <SectionBlock title="Audit log">
                  <AuditTab detail={detail} />
                </SectionBlock>
              </div>
            )}
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

  const items: Array<{
    label: string;
    onClick?: () => void;
    href?: string;
    primary?: boolean;
    danger?: boolean;
  }> = [
    { label: "Assign driver", onClick: actions.onAssignDriver, primary: true },
    { label: "Reassign driver", onClick: actions.onReassignDriver },
    { label: "Mark exception", onClick: () => actions.onMarkException(), danger: true },
    { label: "Cancel order", onClick: actions.onCancel, danger: true },
    { label: "Duplicate order", onClick: actions.onDuplicate },
    { label: "Rebook", onClick: actions.onRebook },
    { label: "Create return", onClick: actions.onCreateReturn },
    { label: "Generate invoice", onClick: actions.onGenerateInvoice },
    { label: "Resend receipt", onClick: actions.onResendReceipt },
    { label: "Refund", onClick: actions.onRefund },
    { label: "Open claim", onClick: actions.onOpenClaim },
    { label: "Open support ticket", onClick: actions.onOpenSupport },
    { label: "Share tracking", onClick: actions.onShareTracking, primary: true },
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
    { label: "Print preview", onClick: actions.onPrintLabels },
    { label: "Print pickup list", onClick: actions.onPrintManifest },
    { label: "Download shipment record", onClick: actions.onDownloadRecord },
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
            variant={item.danger ? "danger" : item.primary ? "primary" : "outline"}
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
  onRefresh,
}: {
  detail: OrderDetail;
  live?: Record<string, unknown> | null;
  onRefresh?: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [shopifyBusy, setShopifyBusy] = useState<string | null>(null);
  const [shopifyErr, setShopifyErr] = useState<string | null>(null);

  async function releaseShopify() {
    setShopifyBusy("release");
    setShopifyErr(null);
    try {
      const token = await getApiToken();
      await ordersApi.shopifyRelease(token, detail.order_id);
      onRefresh?.();
    } catch (e) {
      setShopifyErr(e instanceof Error ? e.message : "Release failed");
    } finally {
      setShopifyBusy(null);
    }
  }

  async function repushShopify() {
    setShopifyBusy("repush");
    setShopifyErr(null);
    try {
      const token = await getApiToken();
      await ordersApi.shopifyRepushFulfillment(token, detail.order_id);
      onRefresh?.();
    } catch (e) {
      setShopifyErr(e instanceof Error ? e.message : "Re-push failed");
    } finally {
      setShopifyBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 font-semibold text-primary">Shipment</h3>
          <Row label="Service" value={detail.service_type || detail.vehicle_class || "—"} />
          <Row
            label="Goods"
            value={
              detail.booking_mode === "vehicle"
                ? "Whole vehicle"
                : (detail.parcels ?? [])
                    .map((parcel) => String(parcel.preset_label || parcel.name || "Parcel"))
                    .join(", ") || "—"
            }
          />
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
      <div>
        <h3 className="mb-3 font-semibold text-primary">Source &amp; references</h3>
        <Row
          label="Source"
          value={detail.order_source_label || orderSourceLabel(detail.order_source)}
        />
        {detail.shopify ? (
          <>
            <Row
              label="Shopify order"
              value={detail.shopify.order_name || detail.shopify.order_id || "—"}
            />
            <Row label="Shop" value={detail.shopify.shop_domain || "—"} />
            <Row label="Fulfillment id" value={detail.shopify.fulfillment_id || "—"} mono />
            <Row
              label="Last tracking push"
              value={
                detail.shopify.last_tracking_push_at
                  ? relativeTime(detail.shopify.last_tracking_push_at)
                  : "—"
              }
            />
            <Row label="Tracking state" value={detail.shopify.last_tracking_state || "—"} />
            {detail.shopify.last_fulfillment_error ? (
              <p className="mt-1 text-xs text-red-700">{detail.shopify.last_fulfillment_error}</p>
            ) : null}
            {detail.shopify.held_for_ops || detail.state === "BOOKED" ? (
              <p className="mt-2 text-xs text-amber-700">
                Held for ops — release to Fleetbase when ready.
              </p>
            ) : null}
            <div className="mt-2 flex flex-wrap gap-2">
              {(detail.shopify.held_for_ops || detail.state === "BOOKED") &&
              detail.order_source === "SHOPIFY" ? (
                <Button
                  variant="primary"
                  className="text-xs"
                  disabled={shopifyBusy === "release"}
                  onClick={() => void releaseShopify()}
                >
                  {shopifyBusy === "release" ? "…" : "Release to Fleetbase"}
                </Button>
              ) : null}
              <Button
                variant="outline"
                className="text-xs"
                disabled={shopifyBusy === "repush"}
                onClick={() => void repushShopify()}
              >
                {shopifyBusy === "repush" ? "…" : "Re-push fulfillment"}
              </Button>
            </div>
            {shopifyErr ? <p className="mt-1 text-xs text-red-700">{shopifyErr}</p> : null}
            {shopifyAdminUrl(detail.shopify) ? (
              <p className="mt-2 text-sm">
                <a
                  className="text-secondary hover:underline"
                  href={shopifyAdminUrl(detail.shopify) ?? undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open in Shopify
                </a>
              </p>
            ) : null}
          </>
        ) : (
          <>
            <Row label="PO" value={detail.purchase_order_number || "—"} />
            <Row label="Internal" value={detail.internal_reference || "—"} />
          </>
        )}
        <Row label="Cost centre" value={detail.cost_centre || "—"} />
      </div>
      {live && Object.keys(live).length > 0 && (
        <div>
          <h3 className="mb-3 font-semibold text-primary">Live execution</h3>
          <div className="rounded-xl bg-gray-bg p-3 text-xs">
            {live.driver_location ? (
              <Row label="Driver GPS" value={JSON.stringify(live.driver_location)} mono />
            ) : null}
            {live.eta ? (
              <Row
                label="Road / scheduled ETA"
                value={
                  typeof live.eta === "object" && live.eta !== null
                    ? [
                        (live.eta as { label?: string }).label,
                        (live.eta as { source?: string }).source
                          ? `(${(live.eta as { source?: string }).source})`
                          : null,
                      ]
                        .filter(Boolean)
                        .join(" ") || JSON.stringify(live.eta)
                    : String(live.eta)
                }
              />
            ) : null}
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
  const customerId = (c360?.id as string | undefined) || detail.customer_id || null;
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
      {customerId ? (
        <Link href={`/customers/${customerId}`}>
          <Button variant="outline" className="px-2 py-1 text-xs">
            <User className="h-4 w-4" /> Customer profile
          </Button>
        </Link>
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

function PackagesTab({ detail, onRefresh }: { detail: OrderDetail; onRefresh?: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [stops, setStops] = useState<Array<Record<string, unknown>>>(detail.stops ?? []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setStops(detail.stops ?? []);
  }, [detail]);

  const amendable = Boolean(detail.parcel_amendable);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      await ordersApi.amendParcels(token, detail.order_id, { stops });
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save parcels");
    } finally {
      setBusy(false);
    }
  }

  if (stops.length) {
    return (
      <div className="space-y-4">
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        {!amendable ? (
          <p className="text-sm text-muted">
            Parcels can be corrected only while the order is booked or ready for dispatch and no
            driver is assigned.
          </p>
        ) : null}
        {stops.map((stop, i) => {
          const packages = Array.isArray(stop.packages) ? stop.packages : [];
          return (
            <div key={i} className="rounded-xl border border-primary/10 p-3 text-sm">
              <p className="mb-2 text-xs font-bold text-muted">
                {String(stop.stop_type || stop.type || `Stop ${i + 1}`)} ·{" "}
                {String(stop.formatted || stop.address || "—")}
              </p>
              {stop.time_window_start || stop.time_window_end ? (
                <p className="mb-2 text-xs text-muted">
                  Window: {stop.time_window_start ? String(stop.time_window_start) : "?"} –{" "}
                  {stop.time_window_end ? String(stop.time_window_end) : "?"}
                </p>
              ) : null}
              {packages.map((pkg, j) => {
                const parcel = (pkg ?? {}) as Record<string, unknown>;
                return (
                  <div key={j} className="mb-3 last:mb-0 rounded-lg bg-gray-bg/40 p-2">
                    <p className="mb-2 text-xs font-semibold">Parcel {j + 1}</p>
                    {amendable ? (
                      <div className="grid gap-2 sm:grid-cols-2">
                        <label className="text-xs">
                          Weight kg
                          <input
                            className="mt-1 w-full rounded-lg border border-primary/15 px-2 py-1"
                            value={parcel.weight_kg == null ? "" : String(parcel.weight_kg)}
                            onChange={(event) =>
                              updateStopPackage(setStops, i, j, { weight_kg: event.target.value })
                            }
                          />
                        </label>
                        <label className="text-xs">
                          Notes
                          <input
                            className="mt-1 w-full rounded-lg border border-primary/15 px-2 py-1"
                            value={parcel.notes == null ? "" : String(parcel.notes)}
                            onChange={(event) =>
                              updateStopPackage(setStops, i, j, { notes: event.target.value })
                            }
                          />
                        </label>
                      </div>
                    ) : (
                      Object.entries(parcel).map(([k, v]) => (
                        <Row
                          key={k}
                          label={k.replace(/_/g, " ")}
                          value={v == null ? "—" : String(v)}
                        />
                      ))
                    )}
                  </div>
                );
              })}
              {!packages.length ? <p className="text-muted">No parcels on this stop.</p> : null}
            </div>
          );
        })}
        {amendable ? (
          <Button type="button" disabled={busy} onClick={() => void save()}>
            {busy ? "Saving…" : "Save parcels and re-quote"}
          </Button>
        ) : null}
      </div>
    );
  }

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

function updateStopPackage(
  setStops: (
    updater: (current: Array<Record<string, unknown>>) => Array<Record<string, unknown>>
  ) => void,
  stopIndex: number,
  parcelIndex: number,
  patch: Record<string, unknown>
) {
  setStops((current) =>
    current.map((stop, i) => {
      if (i !== stopIndex) return stop;
      const packages = Array.isArray(stop.packages) ? [...stop.packages] : [];
      const existing = (packages[parcelIndex] ?? {}) as Record<string, unknown>;
      const next = { ...existing, ...patch };
      if ("weight_kg" in patch) {
        const raw = String(patch.weight_kg ?? "");
        next.weight_kg = raw.trim() === "" ? null : Number(raw);
      }
      packages[parcelIndex] = next;
      return { ...stop, packages };
    })
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
      <div className="mt-3">
        <OrderMoneyDownloads detail={detail} />
      </div>
    </>
  );
}

function DocumentsTab({
  detail,
  onDownloadRecord,
}: {
  detail: OrderDetail;
  onDownloadRecord: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-primary/10 p-4">
        <p className="text-sm text-muted">
          Shipment record includes addresses, PO and references, stops, and the activity trail.
        </p>
        <Button variant="outline" className="mt-3 px-3 py-1.5 text-sm" onClick={onDownloadRecord}>
          Download shipment record
        </Button>
      </div>
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
        {!detail.documents.length && (
          <p className="text-sm text-muted">No other files attached to this order.</p>
        )}
      </ul>
    </div>
  );
}

function PodTab({ pod, orderId }: { pod: Record<string, unknown>; orderId: string }) {
  const { getApiToken } = useAdminAuth();
  const photos = Array.isArray(pod.photos) ? (pod.photos as Array<Record<string, unknown>>) : [];
  const signatures = Array.isArray(pod.signatures)
    ? (pod.signatures as Array<Record<string, unknown>>)
    : [];
  const otps = Array.isArray(pod.otp) ? (pod.otp as Array<Record<string, unknown>>) : [];
  const hasGallery = photos.length + signatures.length + otps.length > 0;

  if (!hasGallery && !Object.keys(pod).length) {
    return (
      <div className="space-y-2">
        <p className="text-sm text-muted">Proof of delivery not yet captured</p>
        <p className="text-xs text-muted">
          Capture in the driver app / Fleetbase — Admin is read-only.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        {pod.source ? (
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted">
            Live from Fleetbase
          </p>
        ) : null}
        {hasGallery ? <PodDownloadAll orderId={orderId} getApiToken={getApiToken} /> : null}
      </div>
      {(photos.length > 0 || signatures.length > 0) && (
        <div className="flex flex-wrap gap-3">
          {photos.map((p, i) =>
            typeof p.url === "string" ? (
              <figure key={String(p.id ?? i)} className="space-y-1">
                {/* eslint-disable-next-line @next/next/no-img-element -- Fleetbase proof URL */}
                <img
                  src={p.url}
                  alt="Delivery photo"
                  className="h-36 w-36 rounded-xl border border-primary/10 object-cover"
                />
                <PodDownloadOne
                  orderId={orderId}
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
                  className="h-36 rounded-xl border border-primary/10 bg-gray-bg object-contain px-4"
                />
                <PodDownloadOne
                  orderId={orderId}
                  getApiToken={getApiToken}
                  slug={s.download}
                  fallbackName={`signature-${i + 1}.png`}
                />
              </figure>
            ) : null;
          })}
        </div>
      )}
      {otps.length > 0 && (
        <div className="space-y-1">
          {otps.map((o, i) => (
            <Row key={i} label="OTP / barcode" value={String(o.otp ?? o.code ?? "—")} mono />
          ))}
        </div>
      )}
      {!hasGallery && pod.event_payload ? (
        <p className="text-xs text-muted">
          POD event recorded — media not synced from Fleetbase yet.
        </p>
      ) : null}
    </div>
  );
}

function CommunicationsTab({ items }: { items: Array<Record<string, unknown>> }) {
  if (!items.length) {
    return (
      <p className="text-sm text-muted">
        No email / SMS / push notifications logged for this order
      </p>
    );
  }
  return (
    <div className="space-y-2">
      {items.map((e, i) => (
        <div
          key={String(e.id ?? i)}
          className="rounded-lg border border-primary/10 px-3 py-2 text-sm"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-medium">{String(e.label || e.event_type)}</p>
            <span className="rounded-full bg-gray-bg px-2 py-0.5 text-[10px] font-bold uppercase text-muted">
              {String(e.channel || "—")} · {String(e.status || "—")}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-muted">
            {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
            {e.recipient ? ` · ${String(e.recipient)}` : ""}
            {e.recipient_type ? ` · ${String(e.recipient_type)}` : ""}
          </p>
          {e.body ? <p className="mt-1 text-xs text-primary/80">{String(e.body)}</p> : null}
          {e.error ? <p className="mt-1 text-xs text-red-600">{String(e.error)}</p> : null}
        </div>
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
