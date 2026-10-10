"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Clock, CreditCard, MapPin, Package, Radio, Sparkles } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { formatState, SLA_STYLES, STATE_STYLES, type OrderDetail } from "@/lib/orders";
import { relativeTime } from "@/lib/crmFormat";
import { Badge } from "@/components/crm/primitives";
import { OrderAssistPanel } from "@/components/orders/OrderAssistPanel";
import { SuperAdminDriverOps } from "@/components/orders/SuperAdminDriverOps";
import { ActionFlash } from "@/components/orders/sections";

import dynamic from "next/dynamic";
import {
  Meta,
  SummaryCard,
  QuickActions,
  SidebarSection,
  SidebarRow,
} from "@/components/orders/order-detail/shared";
import { OverviewTab } from "@/components/orders/order-detail/OverviewTab";
import type { Order360Actions } from "@/components/orders/order-detail/types";
import { PageSkeleton } from "@porterchain/ui/loading";

const tabFallback = () => <PageSkeleton rows={3} />;

const JourneySection = dynamic(
  () => import("@/components/orders/order-detail/JourneySection").then((m) => m.JourneySection),
  { loading: tabFallback }
);
const PartiesSection = dynamic(
  () => import("@/components/orders/order-detail/PartiesSection").then((m) => m.PartiesSection),
  { loading: tabFallback }
);
const MoneySection = dynamic(
  () => import("@/components/orders/order-detail/MoneySection").then((m) => m.MoneySection),
  { loading: tabFallback }
);
const EvidenceSection = dynamic(
  () => import("@/components/orders/order-detail/EvidenceSection").then((m) => m.EvidenceSection),
  { loading: tabFallback }
);
const CareSection = dynamic(
  () => import("@/components/orders/order-detail/CareSection").then((m) => m.CareSection),
  { loading: tabFallback }
);
const SystemSection = dynamic(
  () => import("@/components/orders/order-detail/SystemSection").then((m) => m.SystemSection),
  { loading: tabFallback }
);

export type { Order360Actions };

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
    return <PageSkeleton rows={5} />;
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
    <div className="admin-page flex min-h-[calc(100vh-4rem)] w-full min-w-0 max-w-none flex-col">
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
                <Meta label="Status" value={String(detail.state ?? "—")} />
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
          <SuperAdminDriverOps detail={detail} onRefresh={onRefresh} />

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
                  ? "Driver GPS"
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
          <div key={section} className="rounded-2xl border border-primary/10 bg-white p-5 lg:p-6">
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
              <JourneySection
                detail={detail}
                tracking={tracking}
                live={live}
                onRefresh={onRefresh}
              />
            )}
            {section === "parties" && <PartiesSection detail={detail} />}
            {section === "money" && <MoneySection detail={detail} />}
            {section === "evidence" && (
              <EvidenceSection detail={detail} onDownloadRecord={actions.onDownloadRecord} />
            )}
            {section === "care" && <CareSection detail={detail} />}
            {section === "system" && <SystemSection detail={detail} />}
          </div>
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
