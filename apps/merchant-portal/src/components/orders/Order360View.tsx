"use client";

import { OrderStateBadge } from "@/components/orders/OrderStateBadge";
import Button from "@/components/ui/Button";
import { CopyPublicTrackLink } from "@/components/tracking/CopyPublicTrackLink";
import { downloadMerchantFile, ordersApi, type OrderDetail } from "@/lib/orders";
import { settingsApi } from "@/lib/settings";
import type { LiveTracking } from "@/lib/tracking";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { hasMerchantModule } from "@/lib/merchant-nav";
import { formatCents, formatDate } from "@/lib/utils";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const OverviewTab = dynamic(() => import("./order360/OverviewTab").then((m) => m.OverviewTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const TimelineTab = dynamic(() => import("./order360/TimelineTab").then((m) => m.TimelineTab), {
  loading: () => <PageSkeleton rows={2} />,
});
const TrackingTab = dynamic(() => import("./order360/TrackingTab").then((m) => m.TrackingTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const DriverTab = dynamic(() => import("./order360/DriverTab").then((m) => m.DriverTab), {
  loading: () => <PageSkeleton rows={2} />,
});
const VehicleTab = dynamic(() => import("./order360/VehicleTab").then((m) => m.VehicleTab), {
  loading: () => <PageSkeleton rows={2} />,
});
const PricingTab = dynamic(() => import("./order360/PricingTab").then((m) => m.PricingTab), {
  loading: () => <PageSkeleton rows={2} />,
});
const InvoiceTab = dynamic(() => import("./order360/InvoiceTab").then((m) => m.InvoiceTab), {
  loading: () => <PageSkeleton rows={2} />,
});
const PodTab = dynamic(() => import("./order360/PodTab").then((m) => m.PodTab), {
  loading: () => <PageSkeleton rows={2} />,
});
const SupportTab = dynamic(() => import("./order360/SupportTab").then((m) => m.SupportTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const ClaimsTab = dynamic(() => import("./order360/ClaimsTab").then((m) => m.ClaimsTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const DocumentsTab = dynamic(() => import("./order360/DocumentsTab").then((m) => m.DocumentsTab), {
  loading: () => <PageSkeleton rows={2} />,
});

type Section = "overview" | "journey" | "parties" | "money" | "evidence" | "care";

const SECTIONS: { id: Section; label: string; modules?: string[] }[] = [
  { id: "overview", label: "Overview" },
  { id: "journey", label: "Journey" },
  { id: "parties", label: "Parties" },
  { id: "money", label: "Money", modules: ["invoices"] },
  { id: "evidence", label: "Evidence" },
  { id: "care", label: "Care", modules: ["support", "claims"] },
];

const LEGACY_TAB_TO_SECTION: Record<string, Section> = {
  overview: "overview",
  timeline: "journey",
  tracking: "journey",
  driver: "parties",
  vehicle: "parties",
  pricing: "money",
  invoice: "money",
  pod: "evidence",
  documents: "evidence",
  support: "care",
  claims: "care",
};

function parseOrderSection(value: string | null): Section {
  if (!value) return "overview";
  if (SECTIONS.some((s) => s.id === value)) return value as Section;
  return LEGACY_TAB_TO_SECTION[value] ?? "overview";
}

type Props = {
  detail: OrderDetail;
  tracking: LiveTracking | null;
  liveRefreshing?: boolean;
  onDuplicate: () => void;
  onRefresh: () => void;
  getApiToken?: () => Promise<string>;
  orgId?: string;
};

export function Order360View({
  detail,
  tracking,
  liveRefreshing,
  onDuplicate,
  onRefresh,
  getApiToken,
  orgId,
}: Props) {
  const searchParams = useSearchParams();
  const { modules } = useMerchantAuth();
  const canWriteOrders = hasMerchantModule(modules, "orders_write");
  const canInvoices = hasMerchantModule(modules, "invoices");
  const canSupport = hasMerchantModule(modules, "support");
  const canClaims = hasMerchantModule(modules, "claims");
  const visibleSections = useMemo(
    () =>
      SECTIONS.filter((s) => {
        if (!s.modules?.length) return true;
        if (s.id === "money") return true; // pricing always; invoice gated inside
        if (s.id === "care") return canSupport || canClaims;
        return s.modules.some((m) => hasMerchantModule(modules, m));
      }),
    [modules, canSupport, canClaims]
  );
  const [section, setSection] = useState<Section>(() =>
    parseOrderSection(searchParams.get("section") ?? searchParams.get("tab"))
  );
  const activeSection = visibleSections.some((s) => s.id === section)
    ? section
    : (visibleSections[0]?.id ?? "overview");
  const [recordBusy, setRecordBusy] = useState(false);
  const [recordError, setRecordError] = useState<string | null>(null);
  const [printBusy, setPrintBusy] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [cancelNote, setCancelNote] = useState<string | null>(null);
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailNote, setEmailNote] = useState<string | null>(null);
  const [receiverEmail, setReceiverEmail] = useState(detail.consignee_email ?? "");

  const downloadRecord = async () => {
    if (!getApiToken) return;
    setRecordBusy(true);
    setRecordError(null);
    try {
      const token = await getApiToken();
      await downloadMerchantFile(
        token,
        ordersApi.compliancePdfPath(detail.order_id),
        `shipment-${detail.order_number}.pdf`,
        orgId
      );
    } catch (e) {
      setRecordError(e instanceof Error ? e.message : "Could not download shipment record");
    } finally {
      setRecordBusy(false);
    }
  };

  const downloadPrintPreview = async () => {
    if (!getApiToken) return;
    setPrintBusy(true);
    setRecordError(null);
    try {
      const token = await getApiToken();
      await downloadMerchantFile(
        token,
        ordersApi.printPreviewPath(detail.order_id),
        `print-preview-${detail.tracking_number}.pdf`,
        orgId
      );
    } catch (e) {
      setRecordError(e instanceof Error ? e.message : "Could not download print preview");
    } finally {
      setPrintBusy(false);
    }
  };

  const downloadLabels = async () => {
    if (!getApiToken) return;
    setPrintBusy(true);
    setRecordError(null);
    try {
      const token = await getApiToken();
      await downloadMerchantFile(
        token,
        ordersApi.labelsPdfPath(detail.order_id),
        `labels-${detail.tracking_number}.pdf`,
        orgId
      );
    } catch (e) {
      setRecordError(e instanceof Error ? e.message : "Could not download labels");
    } finally {
      setPrintBusy(false);
    }
  };

  const cancelOrder = async () => {
    if (!getApiToken) return;
    if (
      !window.confirm("Cancel this order? You can cancel until the driver is on the way to pickup.")
    ) {
      return;
    }
    setCancelBusy(true);
    setCancelNote(null);
    try {
      const token = await getApiToken();
      await ordersApi.cancel(token, detail.order_id, orgId);
      setCancelNote("Order cancelled.");
      onRefresh();
    } catch (e) {
      setCancelNote(e instanceof Error ? e.message : "Could not cancel this order.");
    } finally {
      setCancelBusy(false);
    }
  };

  const emailTracking = async () => {
    if (!getApiToken) return;
    setEmailBusy(true);
    setEmailNote(null);
    try {
      const token = await getApiToken();
      const result = await ordersApi.emailTracking(
        token,
        detail.order_id,
        receiverEmail.trim() || undefined,
        orgId
      );
      setEmailNote(`Tracking emailed to ${result.email}`);
    } catch (e) {
      setEmailNote(e instanceof Error ? e.message : "Could not email tracking");
    } finally {
      setEmailBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/orders" className="text-sm text-secondary hover:underline">
            ← Back to orders
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-primary">{detail.tracking_number}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted">
            <OrderStateBadge state={detail.state} displayState={detail.display_state} />
            {detail.is_sandbox ? (
              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-900">
                Sandbox
              </span>
            ) : null}
            <span>{formatCents(detail.amount_cents, detail.currency.toUpperCase())}</span>
            <span>· Scheduled {formatDate(detail.scheduled_at)}</span>
            {liveRefreshing && <span className="text-secondary">Updating…</span>}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!detail.is_sandbox ? (
            <Link
              href={`/track?q=${encodeURIComponent(detail.tracking_number)}`}
              className="inline-flex items-center rounded-xl border border-primary/15 px-3 py-1.5 text-sm hover:bg-gray-bg"
            >
              Open on Track
            </Link>
          ) : null}
          <CopyPublicTrackLink
            trackingNumber={detail.tracking_number}
            publicUrl={tracking?.public_track_url}
            isSandbox={Boolean(detail.is_sandbox)}
            className="rounded-xl border border-primary/15 px-3 py-1.5 text-sm hover:bg-gray-bg"
          />
          {getApiToken && canWriteOrders ? (
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="email"
                className="w-48 rounded-xl border border-primary/15 px-3 py-1.5 text-sm"
                placeholder="Receiver email"
                value={receiverEmail}
                onChange={(e) => setReceiverEmail(e.target.value)}
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => void emailTracking()}
                disabled={emailBusy}
              >
                {emailBusy ? "Sending…" : "Email receiver"}
              </Button>
            </div>
          ) : null}
          <Button size="sm" variant="outline" onClick={onRefresh}>
            Refresh
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => void downloadRecord()}
            disabled={recordBusy}
          >
            {recordBusy ? "Downloading…" : "Download shipment record"}
          </Button>
          <Button size="sm" onClick={() => void downloadLabels()} disabled={printBusy}>
            {printBusy ? "Preparing…" : "Print labels (4×6)"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => void downloadPrintPreview()}
            disabled={printBusy}
          >
            {printBusy ? "Preparing…" : "Dock sheet"}
          </Button>
          {canWriteOrders ? (
            <Button size="sm" variant="outline" onClick={onDuplicate}>
              Duplicate
            </Button>
          ) : null}
          {canWriteOrders && detail.cancel_allowed !== false && detail.state !== "CANCELLED" ? (
            <Button
              size="sm"
              variant="outline"
              onClick={() => void cancelOrder()}
              disabled={cancelBusy}
            >
              {cancelBusy ? "Cancelling…" : "Cancel"}
            </Button>
          ) : null}
        </div>
      </div>

      <nav className="flex flex-wrap gap-1 border-b border-primary/10 pb-1">
        {visibleSections.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setSection(s.id)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              activeSection === s.id
                ? "bg-secondary/10 font-semibold text-secondary"
                : "text-muted hover:text-primary"
            }`}
          >
            {s.label}
          </button>
        ))}
      </nav>

      {activeSection === "overview" && <OverviewTab detail={detail} />}
      {activeSection === "journey" && (
        <div className="space-y-6">
          <TimelineTab timeline={detail.timeline} />
          <TrackingTab
            tracking={tracking}
            onRefresh={onRefresh}
            refreshing={liveRefreshing}
            getApiToken={getApiToken}
            orgId={orgId}
          />
        </div>
      )}
      {activeSection === "parties" && (
        <div className="space-y-6">
          <DriverTab driver={detail.driver} status={detail.driver_status} />
          <VehicleTab vehicle={detail.vehicle} status={detail.vehicle_status} />
        </div>
      )}
      {activeSection === "money" && (
        <div className="space-y-6">
          <PricingTab detail={detail} />
          {canInvoices ? <InvoiceTab detail={detail} /> : null}
        </div>
      )}
      {activeSection === "evidence" && (
        <div className="space-y-6">
          <PodTab
            pod={detail.proof_of_delivery}
            orderId={detail.order_id}
            getApiToken={getApiToken}
            orgId={orgId}
          />
          <DocumentsTab
            documents={detail.documents}
            onDownloadRecord={() => void downloadRecord()}
            onPrintLabels={() => void downloadLabels()}
            onPrintPreview={() => void downloadPrintPreview()}
            busy={recordBusy}
            printBusy={printBusy}
            error={recordError}
          />
        </div>
      )}
      {activeSection === "care" && (
        <div className="space-y-6">
          {canSupport ? (
            <SupportTab
              tickets={detail.support_tickets}
              orderId={detail.order_id}
              getApiToken={getApiToken}
              orgId={orgId}
              onRefresh={onRefresh}
            />
          ) : null}
          {canClaims ? (
            <ClaimsTab
              claims={detail.claims}
              orderId={detail.order_id}
              getApiToken={getApiToken}
              orgId={orgId}
              onRefresh={onRefresh}
            />
          ) : null}
        </div>
      )}
      {recordError && activeSection !== "evidence" ? (
        <p className="text-sm text-red-600">{recordError}</p>
      ) : null}
      {emailNote ? <p className="text-sm text-muted">{emailNote}</p> : null}
      {cancelNote ? <p className="text-sm text-muted">{cancelNote}</p> : null}
      {detail.cancel_rule ? <p className="text-xs text-muted">{detail.cancel_rule}</p> : null}
    </div>
  );
}
