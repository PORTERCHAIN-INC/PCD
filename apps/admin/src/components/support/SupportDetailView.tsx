"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Sparkles } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import {
  formatCategory,
  PRIORITY_STYLES,
  SLA_STYLES,
  STATUS_STYLES,
  type TicketDetail,
} from "@/lib/support";
import { relativeTime } from "@/lib/crmFormat";
import { Badge, Button, Spinner } from "@/components/crm/primitives";

type Tab =
  | "overview"
  | "timeline"
  | "conversation"
  | "customer"
  | "merchant"
  | "driver"
  | "booking"
  | "order"
  | "tracking"
  | "claims"
  | "invoices"
  | "payments"
  | "documents"
  | "attachments"
  | "notes"
  | "audit"
  | "events";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "timeline", label: "Timeline" },
  { id: "conversation", label: "Conversation" },
  { id: "customer", label: "Customer" },
  { id: "merchant", label: "Merchant" },
  { id: "driver", label: "Driver" },
  { id: "booking", label: "Booking" },
  { id: "order", label: "Order" },
  { id: "tracking", label: "Tracking" },
  { id: "claims", label: "Claims" },
  { id: "invoices", label: "Invoices" },
  { id: "payments", label: "Payments" },
  { id: "documents", label: "Documents" },
  { id: "attachments", label: "Attachments" },
  { id: "notes", label: "Internal Notes" },
  { id: "audit", label: "Audit Log" },
  { id: "events", label: "Events" },
];

type Props = {
  detail: TicketDetail | null;
  loading: boolean;
  onStatus: (status: string) => void;
  onAssign: () => void;
  onAutoAssign: () => void;
  onAddNote: (body: string, internal: boolean) => void;
  onPauseSla: () => void;
  onResumeSla: () => void;
};

export default function SupportDetailView({
  detail,
  loading,
  onStatus,
  onAssign,
  onAutoAssign,
  onAddNote,
  onPauseSla,
  onResumeSla,
}: Props) {
  const [tab, setTab] = useState<Tab>("overview");

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }
  if (!detail) return <p className="py-12 text-center text-muted">Ticket not found</p>;

  const smart = detail.smart;
  const sla = detail.sla as Record<string, unknown>;
  const terminal = ["closed", "archived", "resolved"].includes(detail.display_status);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/support"
            className="mb-2 inline-flex items-center gap-1 text-sm text-muted hover:text-secondary"
          >
            <ArrowLeft className="h-4 w-4" /> Support Center
          </Link>
          <h1 className="font-mono text-2xl font-bold text-primary">{detail.ticket_number}</h1>
          <p className="mt-1 text-sm text-primary">{detail.subject}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <span
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-bold",
                STATUS_STYLES[detail.display_status] ?? "bg-gray-100"
              )}
            >
              {detail.display_status.replace(/_/g, " ")}
            </span>
            <span
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-bold capitalize",
                PRIORITY_STYLES[detail.priority] ?? PRIORITY_STYLES.normal
              )}
            >
              {detail.priority}
            </span>
            <span
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-bold capitalize",
                SLA_STYLES[String(sla.status || detail.sla_status)] ?? "bg-gray-100"
              )}
            >
              SLA {String(sla.status || detail.sla_status)}
            </span>
            <Badge tone="blue">{formatCategory(detail.category)}</Badge>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" disabled={terminal} onClick={onAutoAssign}>
            Auto-assign
          </Button>
          <Button variant="outline" disabled={terminal} onClick={onAssign}>
            Assign
          </Button>
          <Button variant="outline" disabled={terminal} onClick={() => onStatus("escalated")}>
            Escalate
          </Button>
          <Button
            variant="outline"
            disabled={terminal}
            onClick={() => onStatus("waiting_customer")}
          >
            Wait customer
          </Button>
          <Button variant="primary" disabled={terminal} onClick={() => onStatus("resolved")}>
            Resolve
          </Button>
          <Button variant="outline" onClick={sla.paused ? onResumeSla : onPauseSla}>
            {sla.paused ? "Resume SLA" : "Pause SLA"}
          </Button>
        </div>
      </div>

      {smart.ai_summary ? (
        <div className="rounded-2xl border border-secondary/20 bg-secondary/5 p-4">
          <p className="flex items-center gap-2 text-xs font-bold uppercase text-secondary">
            <Sparkles className="h-4 w-4" /> AI summary
          </p>
          <p className="mt-2 text-sm text-primary">{String(smart.ai_summary)}</p>
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted">
            {smart.suggested_category ? (
              <span>Suggested category: {String(smart.suggested_category)}</span>
            ) : null}
            {smart.suggested_priority ? (
              <span>Suggested priority: {String(smart.suggested_priority)}</span>
            ) : null}
            {smart.sentiment ? <span>Sentiment: {String(smart.sentiment)}</span> : null}
          </div>
          {(detail.duplicates as unknown[]).length > 0 && (
            <p className="mt-1 text-xs text-amber-700">
              {(detail.duplicates as unknown[]).length} possible duplicate(s)
            </p>
          )}
        </div>
      ) : null}

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
                : "text-muted"
            )}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <motion.div
        key={tab}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-primary/10 bg-white p-6"
      >
        {tab === "overview" && <OverviewTab detail={detail} />}
        {tab === "timeline" && <TimelineTab detail={detail} />}
        {tab === "conversation" && <ConversationTab detail={detail} onAddNote={onAddNote} />}
        {tab === "customer" && <EntityTab data={detail.customer} label="customer" />}
        {tab === "merchant" && <EntityTab data={detail.merchant} label="merchant" />}
        {tab === "driver" && <EntityTab data={detail.driver} label="driver" />}
        {tab === "booking" && <BookingTab detail={detail} />}
        {tab === "order" && <OrderTab detail={detail} />}
        {tab === "tracking" && <TrackingTab detail={detail} />}
        {tab === "claims" && <ClaimsTab detail={detail} />}
        {tab === "invoices" && <InvoiceTab detail={detail} />}
        {tab === "payments" && <PaymentTab detail={detail} />}
        {tab === "documents" && (
          <ListTab items={detail.documents} empty="No documents" field="name" />
        )}
        {tab === "attachments" && (
          <ListTab items={detail.attachments} empty="No attachments" field="name" />
        )}
        {tab === "notes" && <NotesTab detail={detail} onAddNote={onAddNote} />}
        {tab === "audit" && <AuditTab detail={detail} />}
        {tab === "events" && <EventsTab detail={detail} />}
      </motion.div>
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

function OverviewTab({ detail }: { detail: TicketDetail }) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div>
        <Row label="Description" value={detail.description || "—"} />
        <Row label="Agent" value={detail.assigned_agent || "Unassigned"} />
        <Row label="Created" value={relativeTime(detail.created_at)} />
        <Row label="Updated" value={relativeTime(detail.updated_at)} />
      </div>
      <div>
        <Row label="Customer" value={detail.customer_email || "—"} />
        <Row label="Merchant" value={detail.merchant_name || "—"} />
        <Row label="Driver" value={detail.driver_name || "—"} />
        <Row label="Tracking" value={detail.tracking_number || "—"} mono />
      </div>
    </div>
  );
}

function TimelineTab({ detail }: { detail: TicketDetail }) {
  const items = [...detail.timeline].sort((a, b) =>
    String(a.occurred_at).localeCompare(String(b.occurred_at))
  );
  return (
    <ol className="relative border-l-2 border-secondary/20 pl-6">
      {items.map((e, i) => (
        <li key={i} className="relative mb-4">
          <span className="absolute -left-[25px] mt-1 h-3 w-3 rounded-full bg-secondary" />
          <p className="font-semibold text-primary">{String(e.label)}</p>
          <p className="text-xs text-muted">
            {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
          </p>
        </li>
      ))}
      {!items.length && <p className="text-sm text-muted">No timeline events</p>}
    </ol>
  );
}

function ConversationTab({
  detail,
  onAddNote,
}: {
  detail: TicketDetail;
  onAddNote: (body: string, internal: boolean) => void;
}) {
  const all: Array<Record<string, unknown> & { kind: string }> = [
    ...detail.communications.map((c) => ({ ...c, kind: "reply" })),
    ...detail.internal_notes.map((n) => ({ ...n, kind: "internal" })),
  ];
  all.sort((a, b) => String(a.at ?? "").localeCompare(String(b.at ?? "")));
  return (
    <div className="space-y-3">
      {all.map((c, i) => (
        <div
          key={i}
          className={cn(
            "rounded-lg px-3 py-2 text-sm",
            c.kind === "internal" ? "border border-amber-200 bg-amber-50" : "bg-gray-bg"
          )}
        >
          <span className="text-xs text-muted">
            {String(c.channel || c.kind)} · {c.at ? relativeTime(String(c.at)) : ""}
            {c.internal ? " · internal" : ""}
          </span>
          <p className="mt-1">{String(c.body)}</p>
        </div>
      ))}
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={() => {
            const msg = prompt("Reply to customer");
            if (msg) onAddNote(msg, false);
          }}
        >
          Customer reply
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            const msg = prompt("Internal note");
            if (msg) onAddNote(msg, true);
          }}
        >
          Internal note
        </Button>
      </div>
    </div>
  );
}

function EntityTab({
  data,
  label,
}: {
  data: Record<string, unknown> | null | undefined;
  label: string;
}) {
  if (!data) return <p className="text-sm text-muted">No {label} linked</p>;
  return Object.entries(data).map(([k, v]) => (
    <Row key={k} label={k.replace(/_/g, " ")} value={v == null ? "—" : String(v)} />
  ));
}

function BookingTab({ detail }: { detail: TicketDetail }) {
  const b = detail.booking;
  if (!b) return <p className="text-sm text-muted">No booking linked</p>;
  return (
    <>
      <Row label="Booking #" value={String(b.booking_number || "—")} mono />
      <Row label="Booking ID" value={String(b.booking_id || "—")} mono />
    </>
  );
}

function OrderTab({ detail }: { detail: TicketDetail }) {
  const o = detail.order;
  if (!o && !detail.order_id) return <p className="text-sm text-muted">No order linked</p>;
  return (
    <>
      <Row label="Order #" value={String(o?.order_number || detail.order_number || "—")} mono />
      <Row label="State" value={String(o?.state || "—")} />
      <Row label="Amount" value={o?.amount_cents ? formatCents(Number(o.amount_cents)) : "—"} />
      {detail.order_id && (
        <Link
          href={`/orders/${detail.order_id}`}
          className="mt-3 inline-block text-sm text-secondary hover:underline"
        >
          Open Order 360
        </Link>
      )}
    </>
  );
}

function TrackingTab({ detail }: { detail: TicketDetail }) {
  const t = detail.tracking;
  return (
    <>
      <Row
        label="Tracking number"
        value={detail.tracking_number || String(t?.tracking_number || "—")}
        mono
      />
      {detail.order_id && (
        <Link
          href={`/orders/${detail.order_id}`}
          className="mt-3 inline-block text-sm text-secondary hover:underline"
        >
          View live tracking in Order 360
        </Link>
      )}
    </>
  );
}

function ClaimsTab({ detail }: { detail: TicketDetail }) {
  return (
    <ul className="space-y-2">
      {detail.claims.map((c) => (
        <li key={String(c.id)} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          <Link href={`/claims/${c.id}`} className="font-medium text-secondary hover:underline">
            {String(c.claim_type)} — {String(c.status)}
          </Link>
        </li>
      ))}
      {!detail.claims.length && <p className="text-sm text-muted">No linked claims</p>}
    </ul>
  );
}

function InvoiceTab({ detail }: { detail: TicketDetail }) {
  const inv = detail.invoice;
  if (!inv) return <p className="text-sm text-muted">No invoice linked</p>;
  return (
    <>
      <Row label="Invoice #" value={String(inv.invoice_number || "—")} mono />
      <Row label="Status" value={String(inv.status || "—")} />
      <Row label="Amount" value={inv.amount_cents ? formatCents(Number(inv.amount_cents)) : "—"} />
      {inv.pdf_url ? (
        <a
          href={String(inv.pdf_url)}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-secondary hover:underline"
        >
          Download PDF
        </a>
      ) : null}
    </>
  );
}

function PaymentTab({ detail }: { detail: TicketDetail }) {
  const p = detail.payment;
  if (!p) return <p className="text-sm text-muted">No payment linked</p>;
  return (
    <>
      <Row label="Status" value={String(p.status || "—")} />
      <Row label="Amount" value={p.amount_cents ? formatCents(Number(p.amount_cents)) : "—"} />
      <Row label="Payment intent" value={String(p.stripe_payment_intent_id || "—")} mono />
      {p.receipt_url ? (
        <a
          href={String(p.receipt_url)}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-secondary hover:underline"
        >
          Receipt
        </a>
      ) : null}
    </>
  );
}

function NotesTab({
  detail,
  onAddNote,
}: {
  detail: TicketDetail;
  onAddNote: (body: string, internal: boolean) => void;
}) {
  return (
    <div className="space-y-3">
      {detail.internal_notes.map((n, i) => (
        <div key={i} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm">
          <span className="text-xs text-muted">{n.at ? relativeTime(String(n.at)) : ""}</span>
          <p>{String(n.body)}</p>
        </div>
      ))}
      {!detail.internal_notes.length && <p className="text-sm text-muted">No internal notes</p>}
      <Button
        variant="outline"
        onClick={() => {
          const msg = prompt("Internal note");
          if (msg) onAddNote(msg, true);
        }}
      >
        Add note
      </Button>
    </div>
  );
}

function ListTab({
  items,
  empty,
  field,
}: {
  items: Array<Record<string, unknown>>;
  empty: string;
  field: string;
}) {
  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          {String(item[field] || item.id || i)}
        </li>
      ))}
      {!items.length && <p className="text-sm text-muted">{empty}</p>}
    </ul>
  );
}

function AuditTab({ detail }: { detail: TicketDetail }) {
  return (
    <div className="space-y-2">
      {detail.audit_log.map((a, i) => (
        <div key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-xs font-mono">
          {String(a.action)} · {a.created_at ? relativeTime(String(a.created_at)) : ""}
        </div>
      ))}
      {!detail.audit_log.length && <p className="text-sm text-muted">No audit entries</p>}
    </div>
  );
}

function EventsTab({ detail }: { detail: TicketDetail }) {
  return (
    <div className="space-y-2">
      {detail.domain_events.map((e, i) => (
        <div key={i} className="rounded-lg bg-gray-bg px-3 py-2 text-xs font-mono">
          {String(e.event_type)} · {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
        </div>
      ))}
      {!detail.domain_events.length && <p className="text-sm text-muted">No domain events</p>}
    </div>
  );
}
