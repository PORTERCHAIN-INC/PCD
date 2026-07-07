"use client";

import { OrderStateBadge } from "@/components/orders/OrderStateBadge";
import Button from "@/components/ui/Button";
import { LiveTrackingView } from "@/components/tracking/LiveTrackingView";
import { DeliveryTimeline } from "@/components/tracking/DeliveryTimeline";
import { PodGallery } from "@/components/tracking/PodGallery";
import type { OrderDetail } from "@/lib/orders";
import { settingsApi } from "@/lib/settings";
import type { LiveTracking } from "@/lib/tracking";
import { formatCents, formatDate } from "@/lib/utils";
import Link from "next/link";
import type { ReactNode } from "react";
import { useState } from "react";

type Tab =
  | "overview"
  | "timeline"
  | "tracking"
  | "driver"
  | "vehicle"
  | "pricing"
  | "invoice"
  | "pod"
  | "support"
  | "claims"
  | "documents";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "timeline", label: "Timeline" },
  { id: "tracking", label: "Tracking" },
  { id: "driver", label: "Driver" },
  { id: "vehicle", label: "Vehicle" },
  { id: "pricing", label: "Pricing" },
  { id: "invoice", label: "Invoice" },
  { id: "pod", label: "Proof of Delivery" },
  { id: "support", label: "Support" },
  { id: "claims", label: "Claims" },
  { id: "documents", label: "Documents" },
];

type Props = {
  detail: OrderDetail;
  tracking: LiveTracking | null;
  liveRefreshing?: boolean;
  onCancel: () => void;
  onDuplicate: () => void;
  onPrintLabels: () => void;
  onRefresh: () => void;
  getApiToken?: () => Promise<string>;
  orgId?: string;
};

export function Order360View({
  detail,
  tracking,
  liveRefreshing,
  onCancel,
  onDuplicate,
  onPrintLabels,
  onRefresh,
  getApiToken,
  orgId,
}: Props) {
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/orders" className="text-sm text-secondary hover:underline">
            ← Back to orders
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-primary">{detail.tracking_number}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted">
            <OrderStateBadge state={detail.state} />
            <span>{formatCents(detail.amount_cents, detail.currency.toUpperCase())}</span>
            <span>· Scheduled {formatDate(detail.scheduled_at)}</span>
            {liveRefreshing && <span className="text-secondary">Updating…</span>}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={onRefresh}>
            Refresh
          </Button>
          <Button size="sm" variant="outline" onClick={onPrintLabels}>
            Print label
          </Button>
          <Button size="sm" variant="outline" onClick={onDuplicate}>
            Duplicate
          </Button>
          {detail.state !== "CANCELLED" && (
            <Button size="sm" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
        </div>
      </div>

      <nav className="flex flex-wrap gap-1 border-b border-primary/10 pb-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              tab === t.id
                ? "bg-secondary/10 font-semibold text-secondary"
                : "text-muted hover:text-primary"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && <OverviewTab detail={detail} />}
      {tab === "timeline" && <TimelineTab timeline={detail.timeline} />}
      {tab === "tracking" && <TrackingTab tracking={tracking} />}
      {tab === "driver" && <DriverTab driver={detail.driver} status={detail.driver_status} />}
      {tab === "vehicle" && <VehicleTab vehicle={detail.vehicle} status={detail.vehicle_status} />}
      {tab === "pricing" && <PricingTab detail={detail} />}
      {tab === "invoice" && <InvoiceTab detail={detail} />}
      {tab === "pod" && <PodTab pod={detail.proof_of_delivery} />}
      {tab === "support" && (
        <SupportTab
          tickets={detail.support_tickets}
          orderId={detail.order_id}
          getApiToken={getApiToken}
          orgId={orgId}
          onRefresh={onRefresh}
        />
      )}
      {tab === "claims" && (
        <ClaimsTab
          claims={detail.claims}
          orderId={detail.order_id}
          getApiToken={getApiToken}
          orgId={orgId}
          onRefresh={onRefresh}
        />
      )}
      {tab === "documents" && <DocumentsTab documents={detail.documents} />}
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

function OverviewTab({ detail }: { detail: OrderDetail }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Pickup">
        <p>{String(detail.pickup_detail?.formatted ?? detail.pickup)}</p>
      </Card>
      <Card title="Delivery">
        <p>{String(detail.dropoff_detail?.formatted ?? detail.destination)}</p>
      </Card>
      <Card title="References">
        <p>PO: {detail.purchase_order_number ?? "—"}</p>
        <p className="mt-1">Internal: {detail.internal_reference ?? "—"}</p>
      </Card>
      <Card title="Operations">
        <p>Driver: {detail.driver_name ?? "—"}</p>
        <p className="mt-1">Vehicle: {detail.vehicle_label ?? "—"}</p>
        <p className="mt-1">SLA: {detail.sla_status}</p>
      </Card>
      {detail.smart?.ai_summary != null && (
        <Card title="Insights">
          <p className="text-muted">{String(detail.smart.ai_summary)}</p>
        </Card>
      )}
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
            {ev.to_state ? <p className="text-muted">→ {String(ev.to_state)}</p> : null}
            <p className="text-xs text-muted">{String(ev.occurred_at ?? "")}</p>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function TrackingTab({ tracking }: { tracking: LiveTracking | null }) {
  if (tracking?.order_id && tracking?.tracking_number) {
    return <LiveTrackingView tracking={tracking as LiveTracking} />;
  }

  const history = tracking?.tracking_history ?? tracking?.timeline ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Live status">
        <p className="text-muted">Live tracking will appear when the order is in transit.</p>
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
      <p className="mt-1 text-muted">Class: {String(vehicle.vehicle_class ?? "—")}</p>
      <p className="mt-1 text-muted">Plate: {String(vehicle.plate_number ?? "—")}</p>
      <p className="mt-1 text-muted">Status: {status ?? "—"}</p>
    </Card>
  );
}

function PricingTab({ detail }: { detail: OrderDetail }) {
  return (
    <Card title="Pricing">
      <p>
        Quoted: {detail.quote_amount_cents != null ? formatCents(detail.quote_amount_cents) : "—"}
      </p>
      <p className="mt-1">
        Charged: {formatCents(detail.amount_cents, detail.currency.toUpperCase())}
      </p>
      <p className="mt-1 text-muted">Vehicle: {detail.vehicle_class ?? "—"}</p>
      <p className="mt-1 text-muted">Package: {detail.package_type ?? "—"}</p>
      {detail.pricing_breakdown && (
        <pre className="mt-3 overflow-auto rounded-lg bg-gray-50 p-3 text-xs">
          {JSON.stringify(detail.pricing_breakdown, null, 2)}
        </pre>
      )}
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

function PodTab({ pod }: { pod: Record<string, unknown> }) {
  const empty = !pod || Object.keys(pod).length === 0;
  return (
    <Card title="Proof of delivery">
      {empty ? (
        <p className="text-muted">POD will appear after delivery is completed.</p>
      ) : (
        <PodGallery
          pod={
            pod as {
              photos?: Array<Record<string, unknown>>;
              signatures?: Array<Record<string, unknown>>;
              otp?: Array<Record<string, unknown>>;
            }
          }
        />
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
                {String(t.status)} · {String(t.created_at ?? "")}
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

  const submit = async () => {
    if (!getApiToken) return;
    setSubmitting(true);
    try {
      const token = await getApiToken();
      await settingsApi.openClaim(
        token,
        { order_id: orderId, claim_type: claimType, description },
        orgId
      );
      setDescription("");
      onRefresh();
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
            <option value="merchant_complaint">Merchant complaint</option>
            <option value="damaged_parcel">Damaged parcel</option>
            <option value="lost_parcel">Lost parcel</option>
            <option value="late_delivery">Late delivery</option>
          </select>
          <textarea
            className="w-full rounded-lg border px-3 py-2 text-sm"
            rows={2}
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
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
              <p className="font-medium">{String(c.claim_type)}</p>
              <p className="text-muted">
                {String(c.status)} · {String(c.created_at ?? "")}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function DocumentsTab({ documents }: { documents: Array<Record<string, unknown>> }) {
  return (
    <Card title="Documents">
      {documents.length === 0 ? (
        <p className="text-muted">No documents available yet.</p>
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
