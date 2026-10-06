"use client";

import { useState } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";
import Link from "next/link";
import { ArrowLeft, Copy, CreditCard, ExternalLink, RefreshCw, Timer, XCircle } from "lucide-react";
import { formatCents } from "@porterchain/ui/utils";
import { QuoteLines } from "@porterchain/ui/quote-lines";
import { cn } from "@porterchain/ui/utils";
import { PAYMENT_STATUS_STYLES, STATE_STYLES, type BookingDraftDetail } from "@/lib/booking-drafts";
import { relativeTime } from "@/lib/crmFormat";
import { Badge, Button } from "@/components/crm/primitives";
import AdminPage from "@/components/layout/AdminPage";

type Tab =
  | "overview"
  | "quote"
  | "customer"
  | "merchant"
  | "addresses"
  | "package"
  | "pricing"
  | "payment"
  | "timeline"
  | "audit"
  | "events";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "quote", label: "Quote" },
  { id: "customer", label: "Customer" },
  { id: "merchant", label: "Merchant" },
  { id: "addresses", label: "Addresses" },
  { id: "package", label: "Package" },
  { id: "pricing", label: "Pricing" },
  { id: "payment", label: "Payment" },
  { id: "timeline", label: "Timeline" },
  { id: "audit", label: "Audit Log" },
  { id: "events", label: "Events" },
];

type Props = {
  detail: BookingDraftDetail | null;
  loading: boolean;
  actionLoading: boolean;
  onExtend: () => void;
  onCancel: () => void;
  onRestore: () => void;
  onExpire: () => void;
  onDuplicate: () => void;
  onSendPaymentLink: () => void;
};

export default function BookingDraftDetailView({
  detail,
  loading,
  actionLoading,
  onExtend,
  onCancel,
  onRestore,
  onExpire,
  onDuplicate,
  onSendPaymentLink,
}: Props) {
  const [tab, setTab] = useState<Tab>("overview");

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <PageSkeleton rows={3} />
      </div>
    );
  }

  if (!detail) {
    return <p className="py-12 text-center text-sm text-muted">Draft not found</p>;
  }

  const terminal =
    ["BOOKING_CONFIRMED", "CANCELLED"].includes(detail.state) ||
    detail.display_state === "CONVERTED_TO_ORDER";

  return (
    <AdminPage>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/booking-drafts"
            className="mb-2 inline-flex items-center gap-1 text-sm text-muted hover:text-secondary"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to drafts
          </Link>
          <h1 className="font-mono text-2xl font-bold text-primary">{detail.draft_number}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-bold",
                STATE_STYLES[detail.display_state] ?? "bg-gray-100"
              )}
            >
              {detail.display_state.replace(/_/g, " ")}
            </span>
            {detail.is_abandoned && <Badge tone="amber">Abandoned</Badge>}
            {detail.is_expired && <Badge tone="red">Expired</Badge>}
            {detail.amount_cents != null && (
              <span className="text-sm font-semibold text-primary">
                {formatCents(detail.amount_cents)}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {detail.continue_url && (
            <a href={detail.continue_url} target="_blank" rel="noreferrer">
              <Button variant="primary">
                <ExternalLink className="h-4 w-4" />
                Resume booking
              </Button>
            </a>
          )}
          <Button variant="outline" disabled={actionLoading || terminal} onClick={onExtend}>
            <Timer className="h-4 w-4" />
            Extend
          </Button>
          <Button variant="outline" disabled={actionLoading} onClick={onRestore}>
            <RefreshCw className="h-4 w-4" />
            Restore
          </Button>
          <Button
            variant="outline"
            disabled={actionLoading || terminal}
            onClick={onSendPaymentLink}
          >
            <CreditCard className="h-4 w-4" />
            Payment link
          </Button>
          <Button variant="outline" disabled={actionLoading} onClick={onDuplicate}>
            <Copy className="h-4 w-4" />
            Duplicate
          </Button>
          <Button variant="outline" disabled={actionLoading || terminal} onClick={onExpire}>
            Expire
          </Button>
          <Button variant="danger" disabled={actionLoading || terminal} onClick={onCancel}>
            <XCircle className="h-4 w-4" />
            Cancel
          </Button>
        </div>
      </div>

      <nav className="flex gap-1 overflow-x-auto border-b border-primary/10 pb-px">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "shrink-0 rounded-t-lg px-3 py-2 text-sm font-medium",
              tab === t.id
                ? "border border-b-0 border-primary/10 bg-white text-secondary"
                : "text-muted hover:text-primary"
            )}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div key={tab} className="rounded-2xl border border-primary/10 bg-white p-6">
        {tab === "overview" && <OverviewTab detail={detail} />}
        {tab === "quote" && <QuoteTab detail={detail} />}
        {tab === "customer" && <CustomerTab detail={detail} />}
        {tab === "merchant" && <MerchantTab detail={detail} />}
        {tab === "addresses" && <AddressesTab detail={detail} />}
        {tab === "package" && <PackageTab detail={detail} />}
        {tab === "pricing" && <PricingTab detail={detail} />}
        {tab === "payment" && <PaymentTab detail={detail} />}
        {tab === "timeline" && <TimelineTab detail={detail} />}
        {tab === "audit" && <AuditTab detail={detail} />}
        {tab === "events" && <EventsTab detail={detail} />}
      </div>
    </AdminPage>
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

function OverviewTab({ detail }: { detail: BookingDraftDetail }) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div>
        <h3 className="mb-3 text-xs font-bold uppercase text-muted">Draft</h3>
        <Row label="Draft ID" value={detail.draft_id} mono />
        <Row label="Session" value={detail.session_id} mono />
        <Row label="Step" value={detail.current_step} />
        <Row label="Booking type" value={detail.booking_type} />
        <Row label="Created" value={relativeTime(detail.created_at)} />
        <Row label="Updated" value={relativeTime(detail.updated_at)} />
        <Row label="Expires" value={relativeTime(detail.expires_at)} />
      </div>
      <div>
        <h3 className="mb-3 text-xs font-bold uppercase text-muted">Links</h3>
        {detail.booking_id && <Row label="Booking ID" value={detail.booking_id} mono />}
        {detail.order_id && (
          <div className="flex justify-between py-2 text-sm">
            <span className="text-muted">Converted order</span>
            <Link
              href={`/orders/${detail.order_id}`}
              className="font-medium text-secondary hover:underline"
            >
              Open order 360
            </Link>
          </div>
        )}
        {detail.quote_id && <Row label="Quote ID" value={detail.quote_id} mono />}
        {detail.abandoned_minutes != null && (
          <Row label="Abandoned for" value={`${detail.abandoned_minutes} minutes`} />
        )}
      </div>
    </div>
  );
}

function QuoteTab({ detail }: { detail: BookingDraftDetail }) {
  return (
    <>
      <Row label="Quote ID" value={detail.quote_id ?? "—"} mono />
      <Row label="Quote state" value={detail.quote_state ?? "—"} />
      <Row
        label="Quote amount"
        value={detail.quote_amount_cents != null ? formatCents(detail.quote_amount_cents) : "—"}
      />
    </>
  );
}

function CustomerTab({ detail }: { detail: BookingDraftDetail }) {
  return (
    <>
      <Row label="Email" value={detail.customer_email ?? "—"} />
      <Row label="Customer ID" value={detail.customer_id ?? "—"} mono />
      {detail.customer_id && (
        <Link href={`/orders`} className="mt-3 inline-block text-sm text-secondary hover:underline">
          View customer orders
        </Link>
      )}
    </>
  );
}

function MerchantTab({ detail }: { detail: BookingDraftDetail }) {
  return (
    <>
      <Row label="Merchant" value={detail.merchant_name ?? "—"} />
      <Row label="Merchant ID" value={detail.merchant_id ?? "—"} mono />
      {detail.merchant_id && (
        <Link
          href={`/merchants/${detail.merchant_id}`}
          className="mt-3 inline-block text-sm text-secondary hover:underline"
        >
          Open merchant
        </Link>
      )}
    </>
  );
}

function addr(a: Record<string, unknown> | null | undefined): string {
  if (!a) return "—";
  return String(a.formatted ?? a.address ?? JSON.stringify(a));
}

function AddressesTab({ detail }: { detail: BookingDraftDetail }) {
  return (
    <>
      <Row label="Pickup" value={addr(detail.pickup)} />
      <Row label="Dropoff" value={addr(detail.dropoff)} />
      {detail.additional_stops?.length ? (
        <div className="mt-4">
          <h4 className="text-xs font-bold uppercase text-muted">Additional stops</h4>
          {detail.additional_stops.map((s, i) => (
            <Row key={i} label={`Stop ${i + 1}`} value={addr(s)} />
          ))}
        </div>
      ) : null}
    </>
  );
}

function PackageTab({ detail }: { detail: BookingDraftDetail }) {
  return (
    <>
      <Row label="Vehicle" value={detail.vehicle_class ?? "—"} />
      <Row
        label="Package type"
        value={detail.booking_mode === "vehicle" ? "Whole vehicle" : (detail.package_type ?? "—")}
      />
      <Row
        label="Parcels"
        value={
          detail.booking_mode === "vehicle"
            ? "Whole vehicle"
            : (detail.parcels ?? [])
                .map((parcel) => String(parcel.preset_label || "Parcel"))
                .join(", ") || "—"
        }
      />
      <Row label="Weight" value={detail.weight_kg != null ? `${detail.weight_kg} kg` : "—"} />
      <Row label="Dimensions" value={detail.dimensions ?? "—"} />
      <Row
        label="Declared value"
        value={detail.declared_value_cents != null ? formatCents(detail.declared_value_cents) : "—"}
      />
      <Row label="Instructions" value={detail.special_instructions ?? "—"} />
    </>
  );
}

function PricingTab({ detail }: { detail: BookingDraftDetail }) {
  return (
    <QuoteLines
      breakdown={detail.pricing_breakdown}
      quotedCents={detail.quote_amount_cents ?? detail.amount_cents}
      chargedCents={detail.amount_cents}
      currency={(detail.currency || "cad").toUpperCase()}
    />
  );
}

function PaymentTab({ detail }: { detail: BookingDraftDetail }) {
  return (
    <>
      <div className="flex justify-between py-2 text-sm">
        <span className="text-muted">Payment status</span>
        {detail.payment_status ? (
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-xs font-bold",
              PAYMENT_STATUS_STYLES[detail.payment_status] ?? "bg-gray-100"
            )}
          >
            {detail.payment_status}
          </span>
        ) : (
          "—"
        )}
      </div>
      <Row label="Payment ID" value={detail.payment_id ?? "—"} mono />
      <Row label="Stripe session" value={detail.stripe_checkout_session_id ?? "—"} mono />
      <Row label="Payment intent" value={detail.stripe_payment_intent_id ?? "—"} mono />
      <p className="mt-4 text-xs text-muted">
        Bookings are confirmed only via verified Stripe webhooks — never from the frontend
        (masterrule §14).
      </p>
    </>
  );
}

function TimelineTab({ detail }: { detail: BookingDraftDetail }) {
  const items = [...detail.audits].sort((a, b) =>
    String(a.occurred_at).localeCompare(String(b.occurred_at))
  );
  return (
    <ol className="relative border-l-2 border-secondary/20 pl-6">
      {items.map((a, i) => (
        <li key={i} className="mb-6">
          <span className="absolute -left-[9px] mt-1.5 h-4 w-4 rounded-full border-2 border-white bg-secondary" />
          <p className="font-semibold text-primary">{String(a.event_label)}</p>
          <p className="text-xs text-muted">
            {String(a.from_state ?? "—")} → {String(a.to_state)} ·{" "}
            {relativeTime(String(a.occurred_at))}
          </p>
          <p className="text-xs text-muted">Actor: {String(a.actor_type)}</p>
        </li>
      ))}
      {!items.length && <p className="text-sm text-muted">No timeline events yet</p>}
    </ol>
  );
}

function AuditTab({ detail }: { detail: BookingDraftDetail }) {
  return (
    <div className="space-y-3">
      {detail.audits.map((a, i) => (
        <div key={i} className="rounded-lg border border-primary/10 p-3 text-xs">
          <p className="font-semibold">{String(a.event_label)}</p>
          <p className="text-muted">{String(a.occurred_at)}</p>
          <pre className="mt-2 overflow-auto text-muted">{JSON.stringify(a.payload, null, 2)}</pre>
        </div>
      ))}
    </div>
  );
}

function EventsTab({ detail }: { detail: BookingDraftDetail }) {
  return (
    <div className="space-y-2">
      {detail.domain_events.map((e, i) => (
        <div key={i} className="rounded-lg bg-gray-bg px-3 py-2 text-xs">
          <span className="font-mono font-semibold text-secondary">{String(e.event_type)}</span>
          <span className="ml-2 text-muted">
            {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
          </span>
        </div>
      ))}
      {!detail.domain_events.length && <p className="text-sm text-muted">No domain events</p>}
    </div>
  );
}
