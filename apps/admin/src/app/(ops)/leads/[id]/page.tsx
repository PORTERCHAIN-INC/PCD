"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Trash2 } from "lucide-react";
import { hasPermission, useOptionalSessionContext } from "@porterchain/auth";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { Badge, Button, Spinner } from "@/components/crm/primitives";
import {
  LEAD_DECISION_STATUSES,
  LEAD_PRIORITIES,
  LEAD_STATUSES,
  leadsApi,
  leadForm,
  leadIntent,
  leadMessage,
  PRIORITY_TONES,
  STATUS_TONES,
  DECISION_TONES,
} from "@/lib/leads";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { EntityTasks } from "@/components/crm/EntityTasks";

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
        <Spinner />
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
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/leads"
            className="mb-2 inline-flex items-center gap-2 text-sm text-secondary"
          >
            <ArrowLeft className="h-4 w-4" /> Back to leads
          </Link>
          <h1 className="text-2xl font-bold text-primary">{lead.company_name}</h1>
          <p className="text-sm text-muted">{formatWhen(lead.created_at)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={STATUS_TONES[lead.status] ?? "slate"}>{lead.status}</Badge>
          <Badge tone={DECISION_TONES[lead.decision_status ?? "new"] ?? "slate"}>
            {(lead.decision_status ?? "new").replace(/_/g, " ")}
          </Badge>
          <Badge tone={PRIORITY_TONES[lead.priority] ?? "slate"}>{lead.priority}</Badge>
          <Badge tone="slate">Score {lead.lead_score}</Badge>
          {(() => {
            const raw = lead.custom_fields?._score;
            if (!raw || typeof raw !== "object") return null;
            const s = raw as { method?: string; heuristic?: number; predictive?: number | null };
            if (s.method !== "blend") return null;
            return (
              <span className="text-xs text-muted">
                blend h{s.heuristic ?? "—"}/p{s.predictive ?? "—"}
              </span>
            );
          })()}
          <Badge tone="slate">{(lead.channel ?? lead.source).replace(/_/g, " ")}</Badge>
          {lead.status !== "converted" ? (
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
      </div>

      {convertError ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{convertError}</p>
      ) : null}
      {deleteError ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{deleteError}</p>
      ) : null}

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
              label="Captured"
              value={typeof consent.captured_at === "string" ? consent.captured_at : "—"}
            />
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
                    <li key={m.id} className="text-sm">
                      <span className="text-xs text-muted">{m.direction}</span>
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
              {assistLoading ? "Loading…" : `Source: ${assist?.source ?? "—"} · never auto-sends`}
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
                  {assist.risks.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              ) : null}
              <div>
                <p className="mb-1 font-medium text-primary">Suggested reply</p>
                <p className="whitespace-pre-wrap rounded-xl bg-slate-50 p-3">
                  {assist.draft_reply}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button
                    variant="primary"
                    onClick={() => {
                      void (async () => {
                        const token = await getApiToken();
                        await leadsApi.assistDecide(token, id, {
                          proposal_id: "draft_reply",
                          decision: "accept",
                          draft_reply: assist.draft_reply,
                          decision_status: assist.suggested_decision_status,
                        });
                        await qc.invalidateQueries({ queryKey: ["lead", id] });
                        void refetch();
                        void refetchAssist();
                      })();
                    }}
                  >
                    Accept draft + decision
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      void (async () => {
                        const token = await getApiToken();
                        await leadsApi.assistDecide(token, id, {
                          proposal_id: "draft_reply",
                          decision: "reject",
                        });
                      })();
                    }}
                  >
                    Dismiss
                  </Button>
                </div>
              </div>
              {assist.next_questions?.length ? (
                <div>
                  <p className="mb-1 font-medium text-primary">Next questions</p>
                  <ul className="list-disc pl-5">
                    {assist.next_questions.map((q) => (
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
    </div>
  );
}

/** App Router entry — unwraps async params; logic lives in LeadDetailView for tests. */
export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
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
