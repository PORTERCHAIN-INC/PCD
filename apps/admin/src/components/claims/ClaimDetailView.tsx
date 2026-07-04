"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Shield, Sparkles } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { formatCents } from "@porterchain/ui/utils";
import {
  formatClaimType,
  PRIORITY_STYLES,
  STATUS_STYLES,
  type ClaimDetail,
} from "@/lib/claims";
import { relativeTime } from "@/lib/crmFormat";
import { Badge, Button, Spinner } from "@/components/crm/primitives";

type Tab = "overview" | "timeline" | "evidence" | "order" | "investigation" | "compensation" | "insurance" | "communication" | "audit" | "notes";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "timeline", label: "Timeline" },
  { id: "evidence", label: "Evidence" },
  { id: "order", label: "Order" },
  { id: "investigation", label: "Investigation" },
  { id: "compensation", label: "Compensation" },
  { id: "insurance", label: "Insurance" },
  { id: "communication", label: "Communication" },
  { id: "audit", label: "Audit Log" },
  { id: "notes", label: "Notes" },
];

type Props = {
  detail: ClaimDetail | null;
  loading: boolean;
  onStatus: (status: string) => void;
  onAutoAssign: () => void;
  onAddNote: (body: string) => void;
  onAddEvidence: (name: string, type: string) => void;
  onSaveInvestigation: (data: Record<string, string>) => void;
  onSaveCompensation: (approved: number) => void;
  onSaveInsurance: (provider: string) => void;
};

export default function ClaimDetailView({
  detail,
  loading,
  onStatus,
  onAutoAssign,
  onAddNote,
  onAddEvidence,
  onSaveInvestigation,
  onSaveCompensation,
  onSaveInsurance,
}: Props) {
  const [tab, setTab] = useState<Tab>("overview");

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (!detail) return <p className="py-12 text-center text-muted">Claim not found</p>;

  const smart = detail.smart as Record<string, unknown>;
  const terminal = ["closed", "archived", "rejected"].includes(detail.display_status);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/claims" className="mb-2 inline-flex items-center gap-1 text-sm text-muted hover:text-secondary">
            <ArrowLeft className="h-4 w-4" /> Back to claims
          </Link>
          <h1 className="font-mono text-2xl font-bold text-primary">{detail.claim_number}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-bold", STATUS_STYLES[detail.display_status] ?? "bg-gray-100")}>
              {detail.display_status.replace(/_/g, " ")}
            </span>
            <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-bold capitalize", PRIORITY_STYLES[detail.priority] ?? PRIORITY_STYLES.normal)}>
              {detail.priority}
            </span>
            <Badge tone={detail.risk_score >= 70 ? "red" : detail.risk_score >= 40 ? "amber" : "green"}>
              Risk {detail.risk_score}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted">{formatClaimType(detail.claim_type)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" disabled={terminal} onClick={onAutoAssign}>Auto-assign</Button>
          <Button variant="outline" disabled={terminal} onClick={() => onStatus("under_investigation")}>Investigate</Button>
          <Button variant="outline" disabled={terminal} onClick={() => onStatus("approved")}>Approve</Button>
          <Button variant="danger" disabled={terminal} onClick={() => onStatus("rejected")}>Reject</Button>
          <Button variant="primary" disabled={terminal} onClick={() => onStatus("closed")}>Close</Button>
        </div>
      </div>

      {smart.ai_summary ? (
        <div className="rounded-2xl border border-secondary/20 bg-secondary/5 p-4">
          <p className="flex items-center gap-2 text-xs font-bold uppercase text-secondary">
            <Sparkles className="h-4 w-4" /> Smart summary
          </p>
          <p className="mt-2 text-sm text-primary">{String(smart.ai_summary)}</p>
          {smart.suggested_resolution ? (
            <p className="mt-2 text-xs text-muted">Suggested: {String(smart.suggested_resolution)}</p>
          ) : null}
          {(smart.fraud_flags as string[] | undefined)?.length ? (
            <p className="mt-1 text-xs text-red-600">{(smart.fraud_flags as string[]).join(" · ")}</p>
          ) : null}
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
              tab === t.id ? "border border-b-0 border-primary/10 bg-white text-secondary" : "text-muted"
            )}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="rounded-2xl border border-primary/10 bg-white p-6">
        {tab === "overview" && <OverviewTab detail={detail} />}
        {tab === "timeline" && <TimelineTab detail={detail} />}
        {tab === "evidence" && <EvidenceTab detail={detail} onAdd={onAddEvidence} />}
        {tab === "order" && <OrderTab detail={detail} />}
        {tab === "investigation" && <InvestigationTab detail={detail} onSave={onSaveInvestigation} />}
        {tab === "compensation" && <CompensationTab detail={detail} onSave={onSaveCompensation} />}
        {tab === "insurance" && <InsuranceTab detail={detail} onSave={onSaveInsurance} />}
        {tab === "communication" && <CommunicationTab detail={detail} onAddNote={onAddNote} />}
        {tab === "audit" && <AuditTab detail={detail} />}
        {tab === "notes" && <NotesTab detail={detail} onAddNote={onAddNote} />}
      </motion.div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-primary/5 py-2 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className="text-right text-primary">{value}</span>
    </div>
  );
}

function OverviewTab({ detail }: { detail: ClaimDetail }) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div>
        <Row label="Description" value={detail.description || "—"} />
        <Row label="Amount" value={formatCents(detail.amount_cents)} />
        <Row label="Investigator" value={detail.assigned_investigator || "Unassigned"} />
        <Row label="Created" value={relativeTime(detail.created_at)} />
      </div>
      <div>
        <Row label="Customer" value={detail.customer_email || "—"} />
        <Row label="Merchant" value={detail.merchant_name || "—"} />
        <Row label="Driver" value={detail.driver_name || "—"} />
        <Row label="Tracking" value={detail.tracking_number || "—"} />
        {(detail.duplicates as unknown[]).length > 0 && (
          <p className="mt-3 text-xs text-amber-700">{(detail.duplicates as unknown[]).length} duplicate claim(s) on this order</p>
        )}
      </div>
    </div>
  );
}

function TimelineTab({ detail }: { detail: ClaimDetail }) {
  const items = [...detail.timeline].sort((a, b) => String(a.occurred_at).localeCompare(String(b.occurred_at)));
  return (
    <ol className="relative border-l-2 border-secondary/20 pl-6">
      {items.map((e, i) => (
        <li key={i} className="relative mb-4">
          <span className="absolute -left-[25px] mt-1 h-3 w-3 rounded-full bg-secondary" />
          <p className="font-semibold text-primary">{String(e.label)}</p>
          <p className="text-xs text-muted">{e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}</p>
        </li>
      ))}
      {!items.length && <p className="text-sm text-muted">No timeline events</p>}
    </ol>
  );
}

function EvidenceTab({ detail, onAdd }: { detail: ClaimDetail; onAdd: (name: string, type: string) => void }) {
  return (
    <div className="space-y-4">
      <Button variant="outline" onClick={() => {
        const name = prompt("Evidence file name");
        if (name) onAdd(name, "document");
      }}>Upload evidence</Button>
      <ul className="space-y-2">
        {detail.evidence_files.map((f, i) => (
          <li key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
            <span className="font-medium">{String(f.name)}</span>
            <span className="ml-2 text-xs text-muted">{String(f.type)} · v{String(f.version ?? 1)}</span>
          </li>
        ))}
        {!detail.evidence_files.length && <p className="text-sm text-muted">No evidence uploaded</p>}
      </ul>
    </div>
  );
}

function OrderTab({ detail }: { detail: ClaimDetail }) {
  const o = detail.order;
  return (
    <>
      <Row label="Order ID" value={String(o.order_id || detail.order_id)} />
      <Row label="Tracking" value={String(o.tracking_number || detail.tracking_number || "—")} />
      <Row label="State" value={String(o.state || "—")} />
      <Link href={`/orders?search=${o.tracking_number || detail.tracking_number}`} className="mt-3 inline-block text-sm text-secondary hover:underline">
        Open order
      </Link>
    </>
  );
}

function InvestigationTab({ detail, onSave }: { detail: ClaimDetail; onSave: (d: Record<string, string>) => void }) {
  const inv = detail.investigation;
  return (
    <div className="space-y-3">
      {["root_cause", "driver_review", "merchant_review", "customer_review", "internal_notes"].map((field) => (
        <div key={field}>
          <label className="text-xs font-bold uppercase text-muted">{field.replace(/_/g, " ")}</label>
          <p className="mt-1 text-sm text-primary">{String(inv[field] || "—")}</p>
        </div>
      ))}
      <Button variant="outline" onClick={() => {
        const root = prompt("Root cause");
        if (root) onSave({ root_cause: root });
      }}>Update investigation</Button>
    </div>
  );
}

function CompensationTab({ detail, onSave }: { detail: ClaimDetail; onSave: (approved: number) => void }) {
  const c = detail.compensation;
  return (
    <>
      <Row label="Claim amount" value={c.claim_amount_cents ? formatCents(Number(c.claim_amount_cents)) : formatCents(detail.amount_cents)} />
      <Row label="Approved" value={c.approved_amount_cents ? formatCents(Number(c.approved_amount_cents)) : "—"} />
      <Button variant="outline" className="mt-4" onClick={() => {
        const cents = prompt("Approved amount (cents)");
        if (cents) onSave(Number(cents));
      }}>Set compensation</Button>
    </>
  );
}

function InsuranceTab({ detail, onSave }: { detail: ClaimDetail; onSave: (provider: string) => void }) {
  const ins = detail.insurance;
  return (
    <>
      <Row label="Provider" value={String(ins.provider || "—")} />
      <Row label="Policy" value={String(ins.policy_number || "—")} />
      <Row label="Reference" value={String(ins.claim_reference || "—")} />
      <Row label="Status" value={String(ins.status || "—")} />
      <Button variant="outline" className="mt-4" onClick={() => {
        const p = prompt("Insurance provider");
        if (p) onSave(p);
      }}>
        <Shield className="h-4 w-4" /> Update insurance
      </Button>
    </>
  );
}

function CommunicationTab({ detail, onAddNote }: { detail: ClaimDetail; onAddNote: (b: string) => void }) {
  return (
    <div className="space-y-3">
      {detail.communications.map((c, i) => (
        <div key={i} className="rounded-lg bg-gray-bg px-3 py-2 text-sm">
          <span className="text-xs text-muted">{String(c.channel)} · {c.at ? relativeTime(String(c.at)) : ""}</span>
          <p>{String(c.body)}</p>
        </div>
      ))}
      <Button variant="outline" onClick={() => {
        const msg = prompt("Message to party");
        if (msg) onAddNote(msg);
      }}>Add message</Button>
    </div>
  );
}

function AuditTab({ detail }: { detail: ClaimDetail }) {
  return (
    <div className="space-y-2">
      {detail.domain_events.map((e, i) => (
        <div key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-xs font-mono">
          {String(e.event_type)} · {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
        </div>
      ))}
    </div>
  );
}

function NotesTab({ detail, onAddNote }: { detail: ClaimDetail; onAddNote: (b: string) => void }) {
  return (
    <div className="space-y-3">
      {detail.internal_notes.map((n, i) => (
        <div key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          <p>{String(n.body)}</p>
          <p className="text-xs text-muted">{n.created_at ? relativeTime(String(n.created_at)) : ""}</p>
        </div>
      ))}
      <Button variant="outline" onClick={() => {
        const note = prompt("Internal note");
        if (note) onAddNote(note);
      }}>Add note</Button>
    </div>
  );
}
