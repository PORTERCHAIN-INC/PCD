"use client";

import Link from "next/link";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Trash2 } from "lucide-react";
import { hasPermission, useOptionalSessionContext } from "@porterchain/auth";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { Badge, Button } from "@/components/crm/primitives";
import {
  LEAD_DECISION_STATUSES,
  LEAD_PRIORITIES,
  LEAD_STATUSES,
  leadsApi,
  leadForm,
  leadIntent,
  leadMessage,
  PRIORITY_TONES,
} from "@/lib/leads";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { EntityTasks } from "@/components/crm/EntityTasks";
import { LeadDialPanel } from "@/components/leads/LeadDialPanel";
import { cn } from "@porterchain/ui/utils";
import LeadReplyComposer from "@/components/leads/LeadReplyComposer";
import LeadDeskPanel, { LostReasonMenu } from "@/components/leads/LeadDeskPanel";
import { StatusPill } from "@/components/leads/LeadRow";
import { MoreMenu } from "@/components/leads/LeadDeskBits";
import type { ReplyPrefill } from "@/lib/leads";
import AdminPage from "@/components/layout/AdminPage";

function formatWhen(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "full",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function LeadDetailView({ id }: { id: string }) {
  const router = useRouter();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const { profile } = useAdminProfile();
  const session = useOptionalSessionContext()?.session;
  const qc = useQueryClient();
  const [notes, setNotes] = useState("");
  const [prefill, setPrefill] = useState<ReplyPrefill | null>(null);

  // Triage keys on the lead page: r = reply, q = send quote, Esc = leave the box.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (t && (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName))) return;
      if (e.key === "r") {
        e.preventDefault();
        document.getElementById("lead-reply-body")?.focus();
      } else if (e.key === "q") {
        e.preventDefault();
        document.querySelector<HTMLButtonElement>("[data-send-quote]")?.click();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const [saving, setSaving] = useState(false);
  const [converting, setConverting] = useState(false);
  const [convertError, setConvertError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const canDelete =
    hasPermission(session?.permissions, "system:all") || profile?.role === "super_admin";

  const {
    data: lead,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["lead", id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const row = await leadsApi.detail(await getApiToken(), id);
      setNotes(row.internal_notes ?? "");
      return row;
    },
  });

  const { data: conversations = [] } = useQuery({
    queryKey: ["lead-conversations", id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.conversations(await getApiToken(), id),
  });

  const { data: identities = [] } = useQuery({
    queryKey: ["lead-identities", id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.identities(await getApiToken(), id),
  });

  const { data: lead360, refetch: refetch360 } = useQuery({
    queryKey: ["lead-360", id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.get360(await getApiToken(), id),
  });

  const [mergeBusy, setMergeBusy] = useState(false);
  const [mergeError, setMergeError] = useState("");

  async function handleMerge(action: "accept" | "reject") {
    setMergeBusy(true);
    setMergeError("");
    try {
      const token = await getApiToken();
      await leadsApi.resolveMerge(token, id, action);
      await qc.invalidateQueries({ queryKey: ["lead", id] });
      await qc.invalidateQueries({ queryKey: ["lead-360", id] });
      await qc.invalidateQueries({ queryKey: ["leads"] });
      void refetch();
      void refetch360();
    } catch (err) {
      setMergeError(err instanceof Error ? err.message : "Merge failed");
    } finally {
      setMergeBusy(false);
    }
  }

  const {
    data: assist,
    isLoading: assistLoading,
    refetch: refetchAssist,
  } = useQuery({
    queryKey: ["lead-assist", id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.assist(await getApiToken(), id),
  });

  async function save(patch: {
    status?: string;
    priority?: string;
    decision_status?: string;
    internal_notes?: string;
  }) {
    setSaving(true);
    try {
      const token = await getApiToken();
      await leadsApi.update(token, id, patch);
      await qc.invalidateQueries({ queryKey: ["lead", id] });
      await qc.invalidateQueries({ queryKey: ["leads"] });
      void refetch();
    } finally {
      setSaving(false);
    }
  }

  async function handleConvert(
    toMerchant: boolean,
    outcome?: "merchant" | "retail_customer" | "driver_partner"
  ) {
    const branch =
      outcome ??
      (lead?.intent_type as "merchant" | "retail_customer" | "driver_partner" | undefined) ??
      "merchant";
    const label =
      branch === "retail_customer"
        ? "Convert this lead to a retail customer?"
        : branch === "driver_partner"
          ? "Queue this lead for driver-partner onboarding?"
          : toMerchant
            ? "Convert this lead to a company and create an ONBOARDING merchant seat?"
            : "Convert this lead to a CRM company (and deal)?";
    if (!confirm(label)) {
      return;
    }
    setConverting(true);
    setConvertError("");
    try {
      const token = await getApiToken();
      const result = await leadsApi.convert(token, id, {
        to_merchant: toMerchant && branch === "merchant",
        create_deal: branch === "merchant",
        outcome: branch,
      });
      await qc.invalidateQueries({ queryKey: ["lead", id] });
      await qc.invalidateQueries({ queryKey: ["leads"] });
      const merchantId = result.merchant?.merchant_id;
      if (merchantId) {
        router.push(`/merchants/${merchantId}`);
        return;
      }
      if (result.customer_id) {
        router.push(`/customers/${result.customer_id}`);
        return;
      }
      void refetch();
    } catch (err) {
      setConvertError(err instanceof Error ? err.message : "Convert failed");
    } finally {
      setConverting(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this lead permanently?")) return;
    setDeleting(true);
    setDeleteError("");
    try {
      const token = await getApiToken();
      await leadsApi.remove(token, id);
      await qc.invalidateQueries({ queryKey: ["leads"] });
      router.push("/leads");
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Could not delete lead");
      setDeleting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <PageSkeleton rows={3} />
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="space-y-4">
        <Link href="/leads" className="inline-flex items-center gap-2 text-sm text-secondary">
          <ArrowLeft className="h-4 w-4" /> Back to leads
        </Link>
        <p className="text-muted">Lead not found.</p>
      </div>
    );
  }

  const message = leadMessage(lead);
  const intent = leadIntent(lead);
  const form = leadForm(lead);
  const custom = lead.custom_fields ?? {};
  const phoneFull = typeof custom.phone_full === "string" ? custom.phone_full : lead.phone;
  const consent = (lead.consent ?? {}) as Record<string, unknown>;
  const attributionKeys = [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "gclid",
    "fbclid",
    "ref",
    "referral_code",
  ];
  const attribution = attributionKeys
    .map((k) => {
      const v = custom[k];
      return typeof v === "string" && v.trim() ? ([k, v.trim()] as const) : null;
    })
    .filter((x): x is readonly [string, string] => x != null);

  return (
    <AdminPage>
      <header className="space-y-3">
        <Link
          href="/leads"
          className="inline-flex items-center gap-2 text-sm font-semibold text-secondary"
        >
          <ArrowLeft className="h-4 w-4" /> Inbox
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-3xl font-extrabold tracking-tight text-primary sm:text-4xl">
              {lead.company_name}
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              {lead.primary_contact_name ? `${lead.primary_contact_name} · ` : ""}
              {(lead.channel ?? lead.source).replace(/_/g, " ")} · {formatWhen(lead.created_at)}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <StatusPill status={lead.status} />
              <LostReasonMenu lead={lead} />
              {lead.priority === "high" || lead.priority === "urgent" ? (
                <Badge tone={PRIORITY_TONES[lead.priority] ?? "slate"}>{lead.priority}</Badge>
              ) : null}
              {lead360?.sla?.breached ? (
                <span className="text-xs font-semibold text-red-700">Over reply target</span>
              ) : null}
              <span className="text-xs text-slate-600">
                {lead360?.assignee
                  ? `Owner: ${lead360.assignee.name || lead360.assignee.email || lead360.assignee.id}`
                  : lead.assigned_to
                    ? ""
                    : "No owner yet"}
              </span>
            </div>
          </div>
          <MoreMenu>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Convert
            </p>
            <div className="flex flex-wrap gap-2">
              {lead.status !== "won" ? (
                <>
                  <Button
                    variant="outline"
                    onClick={() => void handleConvert(false, "merchant")}
                    disabled={converting}
                  >
                    {converting ? "Converting…" : "Convert to company"}
                  </Button>
                  <Button
                    variant="primary"
                    onClick={() => void handleConvert(true, "merchant")}
                    disabled={converting}
                  >
                    {converting ? "Converting…" : "Convert → merchant"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void handleConvert(false, "retail_customer")}
                    disabled={converting}
                  >
                    → customer
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void handleConvert(false, "driver_partner")}
                    disabled={converting}
                  >
                    → driver partner
                  </Button>
                </>
              ) : null}
              {canDelete ? (
                <Button variant="danger" onClick={() => void handleDelete()} disabled={deleting}>
                  <Trash2 className="h-4 w-4" /> {deleting ? "Deleting…" : "Delete"}
                </Button>
              ) : null}
            </div>
            <p className="text-xs text-slate-500">
              Decision: {(lead.decision_status ?? "new").replace(/_/g, " ")}
            </p>
          </MoreMenu>
        </div>
      </header>

      <LeadDeskPanel lead={lead} onPrefill={setPrefill} />

      {convertError ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{convertError}</p>
      ) : null}
      {deleteError ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{deleteError}</p>
      ) : null}
      {mergeError ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{mergeError}</p>
      ) : null}

      {(lead.merge_candidate_of || lead360?.merge_candidate_of) && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p>
            Merge candidate of{" "}
            <Link
              href={`/leads/${lead.merge_candidate_of || lead360?.merge_candidate_of}`}
              className="font-medium underline"
            >
              {(lead.merge_candidate_of || lead360?.merge_candidate_of || "").slice(0, 8)}…
            </Link>
          </p>
          <div className="flex gap-2">
            <Button
              variant="primary"
              disabled={mergeBusy}
              onClick={() => void handleMerge("accept")}
            >
              Accept merge
            </Button>
            <Button
              variant="outline"
              disabled={mergeBusy}
              onClick={() => void handleMerge("reject")}
            >
              Reject
            </Button>
          </div>
        </div>
      )}

      {lead360?.urgent_unassigned_tasks && lead360.urgent_unassigned_tasks.length > 0 ? (
        <p className="flex items-center gap-2 text-xs text-slate-600" role="note">
          <span className="h-1.5 w-1.5 rounded-full bg-red-600" aria-hidden />
          Open task: {String(lead360.urgent_unassigned_tasks[0]?.title ?? "follow up")}
        </p>
      ) : null}

      <LeadReplyComposer lead={lead} prefill={prefill} />

      <LeadDialPanel lead={lead} />

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Contact">
          <dl className="space-y-2 text-sm">
            <Row label="Name" value={lead.primary_contact_name} />
            <Row label="Email" value={lead.email} />
            <Row label="Phone" value={phoneFull} />
            <Row label="Source" value={lead.source.replace(/_/g, " ")} />
            <Row label="Channel" value={(lead.channel ?? "—").replace(/_/g, " ")} />
            <Row label="Intent type" value={(lead.intent_type ?? "—").replace(/_/g, " ")} />
            {form && <Row label="Form" value={form} />}
            {intent && <Row label="Form intent" value={intent} />}
            {typeof custom.inquiry_type === "string" && (
              <Row label="Inquiry type" value={custom.inquiry_type} />
            )}
            {typeof custom.source_page === "string" && (
              <Row label="Source page" value={custom.source_page} />
            )}
          </dl>
        </Panel>

        <Panel title="Update">
          <div className="space-y-3">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-primary">Status</span>
              <select
                value={lead.status}
                onChange={(e) => void save({ status: e.target.value })}
                disabled={saving}
                className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
              >
                {LEAD_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-primary">Decision status</span>
              <select
                value={lead.decision_status ?? "new"}
                onChange={(e) => void save({ decision_status: e.target.value })}
                disabled={saving}
                className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
              >
                {LEAD_DECISION_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-primary">Priority</span>
              <select
                value={lead.priority}
                onChange={(e) => void save({ priority: e.target.value })}
                disabled={saving}
                className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
              >
                {LEAD_PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-primary">Internal notes</span>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
              />
            </label>
            <Button
              variant="primary"
              disabled={saving}
              onClick={() => void save({ internal_notes: notes })}
            >
              Save notes
            </Button>
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Identities">
          {identities.length === 0 ? (
            <p className="text-sm text-muted">No linked identities yet.</p>
          ) : (
            <ul className="space-y-1.5 text-sm">
              {identities.map((row) => (
                <li key={row.id} className="flex flex-wrap gap-2">
                  <Badge tone="slate">{row.kind.replace(/_/g, " ")}</Badge>
                  <span className="font-mono text-xs text-primary">
                    {row.raw_value || row.value_normalized}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              variant="outline"
              aria-label="Export lead data for data subject request"
              onClick={() => {
                void (async () => {
                  const token = await getApiToken();
                  const data = await leadsApi.privacyExport(token, lead.id);
                  const blob = new Blob([JSON.stringify(data, null, 2)], {
                    type: "application/json",
                  });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `lead-${lead.id}-export.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                })();
              }}
            >
              Export for DSR
            </Button>
            {canDelete ? (
              <>
                <Button
                  variant="outline"
                  aria-label="Request lead privacy erasure"
                  onClick={() => {
                    void (async () => {
                      const token = await getApiToken();
                      await leadsApi.privacyDeleteRequest(token, lead.id, "admin_dsr");
                      void refetch();
                      void refetch360();
                    })();
                  }}
                >
                  Request erasure
                </Button>
                <Button
                  variant="outline"
                  aria-label="Soft-erase personally identifiable information on this lead"
                  onClick={() => {
                    if (
                      !window.confirm(
                        "Soft-erase PII on this lead? Converted+linked leads are blocked."
                      )
                    ) {
                      return;
                    }
                    void (async () => {
                      try {
                        const token = await getApiToken();
                        await leadsApi.privacyErase(token, lead.id);
                        void refetch();
                        void refetch360();
                      } catch (err) {
                        window.alert(err instanceof Error ? err.message : "Erase failed");
                      }
                    })();
                  }}
                >
                  Erase PII
                </Button>
              </>
            ) : null}
          </div>
          <p className="mt-3 text-xs text-muted">
            Processing residency: Canada (Ontario primary). Export includes the lead RoPA inventory
            (purposes, bases, retention). Multi-region residency is not enabled.
          </p>
        </Panel>
        <Panel title="Attribution / visitor">
          {attribution.length === 0 && !lead.referred_by_merchant_id ? (
            <p className="text-sm text-muted">No UTM / click IDs on this lead.</p>
          ) : (
            <dl className="space-y-2 text-sm">
              {lead.referred_by_merchant_id ? (
                <Row label="Referred by merchant" value={lead.referred_by_merchant_id} />
              ) : null}
              {attribution.map(([k, v]) => (
                <Row key={k} label={k} value={v} />
              ))}
            </dl>
          )}
        </Panel>
        <Panel title="Consent">
          <dl className="space-y-2 text-sm">
            <Row label="Marketing" value={consent.marketing ? "yes" : "no"} />
            <Row label="SMS" value={consent.sms ? "yes" : "no"} />
            <Row label="WhatsApp" value={consent.whatsapp ? "yes" : "no"} />
            <Row
              label="Legal basis"
              value={typeof consent.legal_basis === "string" ? consent.legal_basis : "—"}
            />
            <Row
              label="Do not contact"
              value={
                lead360?.nurture && (lead360.nurture as { do_not_contact?: boolean }).do_not_contact
                  ? "yes (suppressed)"
                  : "no"
              }
            />
            <Row
              label="WhatsApp outbound"
              value={(() => {
                const wa = (
                  lead360?.nurture as
                    { whatsapp?: { allowed?: boolean; reason?: string } } | undefined
                )?.whatsapp;
                if (!wa || typeof wa.reason !== "string") return "—";
                return wa.allowed ? `allowed (${wa.reason})` : `blocked (${wa.reason})`;
              })()}
            />
            <Row
              label="Captured"
              value={typeof consent.captured_at === "string" ? consent.captured_at : "—"}
            />
            <Row label="Source" value={typeof consent.source === "string" ? consent.source : "—"} />
            <Row
              label="Text version"
              value={typeof consent.text_version === "string" ? consent.text_version : "—"}
            />
            <Row label="Actor" value={typeof consent.actor === "string" ? consent.actor : "—"} />
            <Row
              label="SLA due"
              value={
                lead.sla_first_response_due_at ? formatWhen(lead.sla_first_response_due_at) : "—"
              }
            />
          </dl>
          {(lead.channel === "whatsapp" || lead.source === "whatsapp") &&
          !(consent.whatsapp === true) ? (
            <p className="mt-3 text-xs text-amber-800">
              WhatsApp templates outside the 24h customer-care window need explicit consent or an
              approved template — do not blast from Assist without accept.
            </p>
          ) : null}
          {(lead.channel === "whatsapp" || lead.source === "whatsapp") && lead.last_touch_at ? (
            <p className="mt-2 text-xs text-muted">
              Last touch {formatWhen(lead.last_touch_at)} — free-form reply window is ~24h from the
              customer&apos;s last inbound message.
            </p>
          ) : null}
        </Panel>
      </div>

      {message && (
        <Panel title="Message">
          <p className="whitespace-pre-wrap text-sm text-primary">{message}</p>
        </Panel>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Journey">
          {lead360?.visitor && Object.keys(lead360.visitor).length > 0 ? (
            <dl className="space-y-2 text-sm">
              <Row
                label="Visitor session"
                value={
                  typeof lead360.visitor.session_id === "string"
                    ? lead360.visitor.session_id
                    : lead.visitor_session_id || "—"
                }
              />
              <Row
                label="Intent score"
                value={
                  lead360.visitor.intent_score != null ? String(lead360.visitor.intent_score) : "—"
                }
              />
              <Row
                label="Guide stage"
                value={(() => {
                  const guide = lead360.visitor.guide;
                  if (guide && typeof guide === "object" && "stage_hint" in guide) {
                    const hint = (guide as { stage_hint?: unknown }).stage_hint;
                    return typeof hint === "string" ? hint : "—";
                  }
                  return "—";
                })()}
              />
              <Row
                label="Retail lead"
                value={
                  lead360.retail_lead
                    ? `${lead360.retail_lead.id.slice(0, 8)} · ${lead360.retail_lead.stage}`
                    : "—"
                }
              />
              <Row
                label="Nurture"
                value={
                  Array.isArray(lead360.nurture?.tags) && lead360.nurture.tags.length
                    ? (lead360.nurture.tags as string[]).join(", ")
                    : lead360.nurture?.marketing_consent
                      ? "marketing consent"
                      : "—"
                }
              />
            </dl>
          ) : (
            <p className="text-sm text-muted">No visitor journey linked yet.</p>
          )}
        </Panel>
        <Panel title="Commerce">
          <div className="space-y-3 text-sm">
            {(lead360?.quotes?.length ?? 0) > 0 ? (
              <div>
                <p className="mb-1 font-medium text-primary">Quotes</p>
                <ul className="space-y-1">
                  {lead360!.quotes.map((q) => (
                    <li key={String(q.id)} className="text-muted">
                      {String(q.id).slice(0, 8)} · {String(q.state)} ·{" "}
                      {q.amount_cents != null
                        ? `$${(Number(q.amount_cents) / 100).toFixed(2)}`
                        : "—"}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {(lead360?.drafts?.length ?? 0) > 0 ? (
              <div>
                <p className="mb-1 font-medium text-primary">Booking drafts</p>
                <ul className="space-y-1">
                  {lead360!.drafts.map((d) => (
                    <li key={d.id} className="flex flex-wrap items-center gap-2">
                      <Link href={`/booking-drafts/${d.id}`} className="underline">
                        {d.id.slice(0, 8)}
                      </Link>
                      <span className="text-muted">{d.state}</span>
                      {d.draft_abandoned ? (
                        <Badge tone="amber">draft abandoned ({d.draft_abandoned_reason})</Badge>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-muted">No booking drafts.</p>
            )}
            {(lead360?.abandoned_checkouts?.length ?? 0) > 0 ? (
              <div>
                <p className="mb-1 font-medium text-primary">Stripe abandoned checkouts</p>
                <ul className="space-y-1">
                  {lead360!.abandoned_checkouts.map((a) => (
                    <li key={a.id} className="text-muted">
                      <Badge tone="red">stripe abandoned</Badge> {a.reason} · quote{" "}
                      {a.quote_id.slice(0, 8)}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {lead360?.referral ? (
              <Row
                label="Referral credit"
                value={`${String(lead360.referral.status)} · ${String(lead360.referral.amount_cents ?? 0)}¢`}
              />
            ) : null}
          </div>
        </Panel>
      </div>

      {conversations.length > 0 ? (
        <Panel title="Conversations">
          <div className="space-y-4">
            {conversations.map((c) => (
              <div key={c.id} className="rounded-xl border border-primary/10 p-3">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                  {c.channel.replace(/_/g, " ")} · {c.status}
                </p>
                <ul className="space-y-2">
                  {c.messages.map((m) => (
                    <li
                      key={m.id}
                      className={cn(
                        "max-w-[85%] rounded-xl px-3 py-2 text-sm",
                        m.direction === "outbound" ? "ml-auto bg-secondary/10" : "bg-slate-100"
                      )}
                    >
                      <span className="text-xs text-muted">
                        {m.direction === "outbound"
                          ? "PorterChain"
                          : m.direction === "inbound"
                            ? "Lead"
                            : m.direction}
                        {m.occurred_at ? ` · ${new Date(m.occurred_at).toLocaleString()}` : ""}
                      </span>
                      <p className="whitespace-pre-wrap text-primary">{m.body}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}

      <Panel title="Lead Assist">
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <p className="text-muted">
              {assistLoading
                ? "Updating…"
                : `Source: ${assist?.source ?? "—"} · writes require confirm`}
            </p>
            <Button variant="outline" onClick={() => void refetchAssist()}>
              Refresh
            </Button>
          </div>
          {assist ? (
            <>
              <p className="text-primary">{assist.summary}</p>
              {assist.risks?.length ? (
                <ul className="list-disc pl-5 text-amber-800">
                  {assist.risks.map((r: string) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              ) : null}
              <div className="space-y-3">
                {(
                  (assist.proposals as Array<{
                    id: string;
                    type?: string;
                    title?: string;
                    body?: string;
                  }>) || [
                    {
                      id: "draft_reply",
                      title: "Suggested reply",
                      body: assist.draft_reply,
                    },
                    {
                      id: "decision_status",
                      title: "Suggested decision",
                      body: assist.suggested_decision_status,
                    },
                  ]
                ).map((proposal) => (
                  <div key={proposal.id} className="rounded-xl border border-primary/10 p-3">
                    <p className="mb-1 font-medium text-primary">{proposal.title || proposal.id}</p>
                    <p className="whitespace-pre-wrap text-sm text-primary/90">
                      {proposal.body || "—"}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button
                        variant="primary"
                        onClick={() => {
                          void (async () => {
                            const token = await getApiToken();
                            await leadsApi.assistDecide(token, id, {
                              proposal_id: proposal.id,
                              decision: "accept",
                              draft_reply:
                                proposal.id === "draft_reply"
                                  ? String(proposal.body || assist.draft_reply || "")
                                  : undefined,
                              decision_status:
                                proposal.id === "decision_status"
                                  ? String(proposal.body || assist.suggested_decision_status || "")
                                  : undefined,
                            });
                            await qc.invalidateQueries({ queryKey: ["lead", id] });
                            void refetch();
                            void refetchAssist();
                            void refetch360();
                          })();
                        }}
                      >
                        Accept
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          void (async () => {
                            const token = await getApiToken();
                            await leadsApi.assistDecide(token, id, {
                              proposal_id: proposal.id,
                              decision: "reject",
                            });
                            void refetchAssist();
                          })();
                        }}
                      >
                        Dismiss
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
              {assist.next_questions?.length ? (
                <div>
                  <p className="mb-1 font-medium text-primary">Next questions</p>
                  <ul className="list-disc pl-5">
                    {assist.next_questions.map((q: string) => (
                      <li key={q}>{q}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      </Panel>

      {(typeof custom.utm_source === "string" ||
        typeof custom.utm_campaign === "string" ||
        typeof custom.utm_medium === "string") && (
        <Panel title="Attribution">
          <dl className="space-y-2 text-sm">
            {typeof custom.utm_source === "string" && (
              <Row label="UTM source" value={custom.utm_source} />
            )}
            {typeof custom.utm_campaign === "string" && (
              <Row label="UTM campaign" value={custom.utm_campaign} />
            )}
            {typeof custom.utm_medium === "string" && (
              <Row label="UTM medium" value={custom.utm_medium} />
            )}
          </dl>
        </Panel>
      )}

      {typeof custom.transcript_summary === "string" && custom.transcript_summary.trim() && (
        <Panel title="Guide summary">
          <p className="whitespace-pre-wrap text-sm text-primary">{custom.transcript_summary}</p>
        </Panel>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Conversation">
          <ActivityTimeline entityType="lead" entityId={id} />
        </Panel>
        <Panel title="Tasks & appointments">
          <EntityTasks entityType="lead" entityId={id} />
        </Panel>
      </div>
      <div className="h-24 md:hidden" aria-hidden />
    </AdminPage>
  );
}

/** App Router entry — unwraps async params; logic lives in LeadDetailView for tests. */
export default function LeadDetailClient({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <LeadDetailView id={id} />;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <h2 className="mb-4 font-semibold text-primary">{title}</h2>
      {children}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex justify-between gap-4 border-b border-primary/5 py-2">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-medium text-primary">{value ?? "—"}</dd>
    </div>
  );
}
