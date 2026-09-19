"use client";

import { QuoteLines } from "@/components/billing/QuoteLines";
import { OrderStateBadge } from "@/components/orders/OrderStateBadge";
import Button from "@/components/ui/Button";
import { CopyPublicTrackLink } from "@/components/tracking/CopyPublicTrackLink";
import { LiveTrackingView } from "@/components/tracking/LiveTrackingView";
import { DeliveryTimeline } from "@/components/tracking/DeliveryTimeline";
import { PodGallery } from "@/components/tracking/PodGallery";
import {
  claimStatusLabel,
  claimTypeLabel,
  orderSourceLabel,
  orderStateLabel,
  packageLabel,
  slaStatusLabel,
  ticketStatusLabel,
  vehicleLabel,
} from "@/lib/catalog";
import { downloadMerchantFile, ordersApi, type OrderDetail } from "@/lib/orders";
import { settingsApi } from "@/lib/settings";
import type { LiveTracking } from "@/lib/tracking";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { hasMerchantModule } from "@/lib/merchant-nav";
import { formatCents, formatDate } from "@/lib/utils";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";

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

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-5">
      <h2 className="font-semibold text-primary">{title}</h2>
      <div className="mt-3 text-sm">{children}</div>
    </section>
  );
}

function pickupWindowFromStops(stops?: Array<Record<string, unknown>> | null): string | null {
  const pickup = (stops || []).find((stop) => {
    const kind = String(stop.stop_type || stop.type || "").toLowerCase();
    return kind === "pickup" || kind === "pick";
  });
  if (!pickup) return null;
  const start = pickup.time_window_start;
  const end = pickup.time_window_end;
  if (!start && !end) return null;
  return `${start ? formatDate(String(start)) : "?"} – ${end ? formatDate(String(end)) : "?"}`;
}

function OverviewTab({ detail }: { detail: OrderDetail }) {
  const pickupWindow = pickupWindowFromStops(detail.stops);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Pickup">
        <p>{String(detail.pickup_detail?.formatted ?? detail.pickup)}</p>
      </Card>
      <Card title="Delivery">
        <p>{String(detail.dropoff_detail?.formatted ?? detail.destination)}</p>
      </Card>
      <Card title="References">
        <p>Source: {detail.order_source_label || orderSourceLabel(detail.order_source)}</p>
        {detail.shopify ? (
          <>
            <p className="mt-1">
              Shopify order: {detail.shopify.order_name || detail.shopify.order_id || "—"}
            </p>
            {detail.shopify.shop_domain ? (
              <p className="mt-1">Shop: {detail.shopify.shop_domain}</p>
            ) : null}
          </>
        ) : (
          <>
            <p className="mt-1">PO: {detail.purchase_order_number ?? "—"}</p>
            <p className="mt-1">Internal: {detail.internal_reference ?? "—"}</p>
          </>
        )}
        <p className="mt-1">Cost centre: {detail.cost_centre ?? "—"}</p>
      </Card>
      <Card title="Operations">
        <p>Driver: {detail.driver_name ?? "—"}</p>
        <p className="mt-1">
          Vehicle: {detail.vehicle_label ?? vehicleLabel(detail.vehicle_class)}
        </p>
        <p className="mt-1">SLA: {slaStatusLabel(detail.sla_status)}</p>
        {pickupWindow ? <p className="mt-1">Pickup window: {pickupWindow}</p> : null}
      </Card>
      {detail.stops?.length || detail.packages?.length ? (
        <Card title="Stops and parcels">
          {detail.stops?.length
            ? detail.stops.map((stop, i) => (
                <div key={i} className="mb-3 last:mb-0">
                  <p className="font-medium">
                    {String(stop.stop_type || stop.type || `Stop ${i + 1}`)} ·{" "}
                    {String(stop.formatted || stop.address || "—")}
                  </p>
                  {stop.time_window_start || stop.time_window_end ? (
                    <p className="text-xs text-muted">
                      Window:{" "}
                      {stop.time_window_start ? formatDate(String(stop.time_window_start)) : "?"} –{" "}
                      {stop.time_window_end ? formatDate(String(stop.time_window_end)) : "?"}
                    </p>
                  ) : null}
                  {Array.isArray(stop.packages) && stop.packages.length > 0 ? (
                    <ul className="mt-1 list-disc pl-5 text-muted">
                      {(stop.packages as Array<Record<string, unknown>>).map((pkg, j) => (
                        <li key={j}>
                          {String(pkg.name || pkg.sku || `Parcel ${j + 1}`)}
                          {pkg.weight_kg != null ? ` · ${String(pkg.weight_kg)} kg` : ""}
                          {pkg.notes ? ` · ${String(pkg.notes)}` : ""}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ))
            : detail.packages.map((pkg, i) => (
                <p key={i} className="mt-1">
                  {String(pkg.name || pkg.package_type || `Parcel ${i + 1}`)}
                  {pkg.weight_kg != null ? ` · ${String(pkg.weight_kg)} kg` : ""}
                </p>
              ))}
          {detail.route_import_job_id ? (
            <Link
              className="mt-2 inline-block text-secondary hover:underline"
              href={`/routes/${detail.route_import_job_id}`}
            >
              Open route job
            </Link>
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}

function TimelineTab({ timeline }: { timeline: Array<Record<string, unknown>> }) {
  return (
    <Card title="Order timeline">
      <ol className="space-y-3">
        {timeline.length === 0 && <li className="text-muted">No events yet.</li>}
        {timeline.map((ev, i) => (
          <li key={i} className="border-l-2 border-secondary/30 pl-4">
            <p className="font-medium">{String(ev.label ?? ev.event_type)}</p>
            {ev.to_state ? (
              <p className="text-muted">→ {orderStateLabel(String(ev.to_state))}</p>
            ) : null}
            <p className="text-xs text-muted">
              {ev.occurred_at ? formatDate(String(ev.occurred_at)) : ""}
            </p>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function TrackingTab({
  tracking,
  onRefresh,
  refreshing,
  getApiToken,
  orgId,
}: {
  tracking: LiveTracking | null;
  onRefresh: () => void;
  refreshing?: boolean;
  getApiToken?: () => Promise<string>;
  orgId?: string;
}) {
  if (tracking?.order_id && tracking?.tracking_number) {
    return (
      <LiveTrackingView
        tracking={tracking}
        onRefresh={onRefresh}
        refreshing={refreshing}
        showOrderLink={false}
        getApiToken={getApiToken}
        orgId={orgId}
      />
    );
  }

  const history = tracking?.tracking_history ?? tracking?.timeline ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Live status">
        <p className="text-muted">Live location appears once a driver is on the way.</p>
      </Card>
      <Card title="Tracking history">
        <DeliveryTimeline events={history} />
      </Card>
    </div>
  );
}

function DriverTab({
  driver,
  status,
}: {
  driver: Record<string, unknown> | null | undefined;
  status?: string | null;
}) {
  if (!driver) return <Card title="Driver">No driver assigned yet.</Card>;
  return (
    <Card title="Driver">
      <p className="font-medium">{String(driver.name ?? "—")}</p>
      <p className="mt-1 text-muted">Phone: {String(driver.phone ?? "—")}</p>
      <p className="mt-1 text-muted">
        Status: {status ?? String(driver.is_online ? "online" : "offline")}
      </p>
      {driver.rating != null && <p className="mt-1 text-muted">Rating: {String(driver.rating)}</p>}
    </Card>
  );
}

function VehicleTab({
  vehicle,
  status,
}: {
  vehicle: Record<string, unknown> | null | undefined;
  status?: string | null;
}) {
  if (!vehicle) return <Card title="Vehicle">No vehicle assigned yet.</Card>;
  return (
    <Card title="Vehicle">
      <p className="font-medium">{String(vehicle.label ?? "—")}</p>
      <p className="mt-1 text-muted">Class: {vehicleLabel(String(vehicle.vehicle_class ?? ""))}</p>
      <p className="mt-1 text-muted">Plate: {String(vehicle.plate_number ?? "—")}</p>
      <p className="mt-1 text-muted">Status: {status ?? "—"}</p>
    </Card>
  );
}

function PricingTab({ detail }: { detail: OrderDetail }) {
  const currency = detail.currency.toUpperCase();
  return (
    <Card title="Pricing">
      <p className="text-muted">Vehicle: {vehicleLabel(detail.vehicle_class)}</p>
      <p className="mt-1 text-muted">Package: {packageLabel(detail.package_type)}</p>
      <div className="mt-3">
        <QuoteLines
          breakdown={detail.pricing_breakdown}
          quotedCents={detail.quote_amount_cents}
          chargedCents={detail.amount_cents}
          currency={currency}
        />
      </div>
      {detail.quote_amount_cents == null && !detail.pricing_breakdown ? (
        <p className="mt-2 text-muted">
          Charged: {formatCents(detail.amount_cents, currency)} · no stored quote on this order
        </p>
      ) : null}
    </Card>
  );
}

function InvoiceTab({ detail }: { detail: OrderDetail }) {
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

function PodTab({
  pod,
  orderId,
  getApiToken,
  orgId,
}: {
  pod: Record<string, unknown>;
  orderId: string;
  getApiToken?: () => Promise<string>;
  orgId?: string;
}) {
  const empty = !pod || Object.keys(pod).length === 0;
  return (
    <Card title="Proof of delivery">
      {empty ? (
        <p className="text-muted">POD will appear after delivery is completed.</p>
      ) : (
        <PodGallery pod={pod} orderId={orderId} getToken={getApiToken} orgId={orgId} />
      )}
    </Card>
  );
}

function SupportTab({
  tickets,
  orderId,
  getApiToken,
  orgId,
  onRefresh,
}: {
  tickets: Array<Record<string, unknown>>;
  orderId: string;
  getApiToken?: () => Promise<string>;
  orgId?: string;
  onRefresh: () => void;
}) {
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!getApiToken || !subject.trim()) return;
    setSubmitting(true);
    try {
      const token = await getApiToken();
      await settingsApi.createTicket(
        token,
        { subject, description, order_id: orderId, category: "merchant_support" },
        orgId
      );
      setSubject("");
      setDescription("");
      onRefresh();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card title="Support tickets">
      {getApiToken && (
        <div className="mb-4 space-y-2 border-b border-primary/10 pb-4">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <textarea
            className="w-full rounded-lg border px-3 py-2 text-sm"
            rows={2}
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Button size="sm" onClick={() => void submit()} disabled={submitting}>
            Open ticket
          </Button>
        </div>
      )}
      {tickets.length === 0 ? (
        <p className="text-muted">No support tickets for this order.</p>
      ) : (
        <ul className="space-y-2">
          {tickets.map((t) => (
            <li key={String(t.id)} className="rounded-lg border border-primary/10 p-3">
              <p className="font-medium">{String(t.subject)}</p>
              <p className="text-muted">
                {ticketStatusLabel(String(t.status))}
                {t.created_at ? ` · ${formatDate(String(t.created_at))}` : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function ClaimsTab({
  claims,
  orderId,
  getApiToken,
  orgId,
  onRefresh,
}: {
  claims: Array<Record<string, unknown>>;
  orderId: string;
  getApiToken?: () => Promise<string>;
  orgId?: string;
  onRefresh: () => void;
}) {
  const [claimType, setClaimType] = useState("merchant_complaint");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!getApiToken) return;
    setSubmitting(true);
    setError(null);
    try {
      const token = await getApiToken();
      await settingsApi.openClaim(
        token,
        { order_id: orderId, claim_type: claimType, description },
        orgId
      );
      setDescription("");
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That order was not found.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card title="Claims">
      {getApiToken && (
        <div className="mb-4 space-y-2 border-b border-primary/10 pb-4">
          <select
            className="w-full rounded-lg border px-3 py-2 text-sm"
            value={claimType}
            onChange={(e) => setClaimType(e.target.value)}
          >
            <option value="merchant_complaint">{claimTypeLabel("merchant_complaint")}</option>
            <option value="damaged_parcel">{claimTypeLabel("damaged_parcel")}</option>
            <option value="lost_parcel">{claimTypeLabel("lost_parcel")}</option>
            <option value="late_delivery">{claimTypeLabel("late_delivery")}</option>
          </select>
          <textarea
            className="w-full rounded-lg border px-3 py-2 text-sm"
            rows={2}
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button size="sm" onClick={() => void submit()} disabled={submitting}>
            File claim
          </Button>
        </div>
      )}
      {claims.length === 0 ? (
        <p className="text-muted">No claims filed for this order.</p>
      ) : (
        <ul className="space-y-2">
          {claims.map((c) => (
            <li key={String(c.id)} className="rounded-lg border border-primary/10 p-3">
              <p className="font-medium">{claimTypeLabel(String(c.claim_type))}</p>
              <p className="text-muted">
                {claimStatusLabel(String(c.status))}
                {c.created_at ? ` · ${formatDate(String(c.created_at))}` : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function DocumentsTab({
  documents,
  onDownloadRecord,
  onPrintLabels,
  onPrintPreview,
  busy,
  printBusy,
  error,
}: {
  documents: Array<Record<string, unknown>>;
  onDownloadRecord: () => void;
  onPrintLabels: () => void;
  onPrintPreview: () => void;
  busy: boolean;
  printBusy: boolean;
  error: string | null;
}) {
  return (
    <Card title="Documents">
      <div className="mb-4 space-y-2 border-b border-primary/10 pb-4">
        <p className="text-sm text-muted">
          Download a shipment record: addresses, references, stops, and the activity trail.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={onPrintLabels} disabled={printBusy}>
            {printBusy ? "Preparing…" : "Print labels (4×6)"}
          </Button>
          <Button size="sm" variant="outline" onClick={onDownloadRecord} disabled={busy}>
            {busy ? "Downloading…" : "Download shipment record"}
          </Button>
          <Button size="sm" variant="outline" onClick={onPrintPreview} disabled={printBusy}>
            {printBusy ? "Preparing…" : "Dock sheet"}
          </Button>
        </div>
        <p className="text-xs text-muted">
          Labels are one 4×6 page per box (QR). Dock sheet is addresses only — not a carrier label.
        </p>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </div>
      {documents.length === 0 ? (
        <p className="text-muted">No other files attached to this order.</p>
      ) : (
        <ul className="space-y-2">
          {documents.map((d, i) => (
            <li key={i}>
              <a
                href={String(d.url)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-secondary hover:underline"
              >
                {String(d.name ?? d.type)}
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
