"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Badge, Button, Spinner } from "@/components/crm/primitives";
import { DRIVER_LEAD_SOURCE } from "@/lib/admin-nav";
import AdminPage from "@/components/layout/AdminPage";
import {
  LEAD_CHANNELS,
  LEAD_DECISION_STATUSES,
  LEAD_INTENT_TYPES,
  LEAD_PRIORITIES,
  LEAD_STATUSES,
  leadsApi,
  leadForm,
  leadIntent,
  LEAD_SOURCES,
  PRIORITY_TONES,
  STATUS_TONES,
  DECISION_TONES,
  type LeadFilters,
} from "@/lib/leads";

function formatWhen(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function sourceLabel(source: string): string {
  if (source === DRIVER_LEAD_SOURCE) return "driver partner";
  return source.replace(/_/g, " ");
}

export default function LeadsListClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const searchParams = useSearchParams();
  const sourceFromUrl = searchParams.get("source") ?? undefined;
  const isDriverInbox = sourceFromUrl === DRIVER_LEAD_SOURCE;
  const [filters, setFilters] = useState<LeadFilters>(() =>
    sourceFromUrl ? { source: sourceFromUrl } : {}
  );
  const [showCapture, setShowCapture] = useState(false);
  const [captureBusy, setCaptureBusy] = useState(false);
  const [captureError, setCaptureError] = useState("");
  const [capture, setCapture] = useState({
    company_name: "",
    primary_contact_name: "",
    email: "",
    phone: "",
    source: "phone_call",
    channel: "phone_call",
    internal_notes: "",
    consent_marketing: false,
    consent_sms: false,
    consent_whatsapp: false,
  });

  useEffect(() => {
    setFilters((f) => {
      if (f.source === sourceFromUrl) return f;
      return { ...f, source: sourceFromUrl };
    });
  }, [sourceFromUrl]);

  const {
    data: rows = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["leads", JSON.stringify(filters)],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.list(await getApiToken(), filters),
  });

  const { data: metrics } = useQuery({
    queryKey: ["lead-metrics"],
    enabled: isLoaded && !isDriverInbox && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.metrics(await getApiToken(), 30),
  });

  const { data: referralCredits = [] } = useQuery({
    queryKey: ["lead-referral-credits"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.referralCredits(await getApiToken()),
  });

  return (
    <AdminPage>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">
            {isDriverInbox ? "Driver Applications" : "Merchant Leads"}
          </h1>
          <p className="text-sm text-muted">
            {isDriverInbox
              ? "Vehicle partner applications from /vehicle-partner"
              : "Multi-channel merchant acquisition inbox (website, social, WhatsApp, call, referral)"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {!isDriverInbox ? (
            <>
              <button
                type="button"
                onClick={() => setShowCapture(true)}
                className="inline-flex items-center rounded-xl border border-primary/10 px-3 py-2 text-sm font-medium text-secondary hover:bg-slate-50"
              >
                Add lead
              </button>
              <button
                type="button"
                onClick={() =>
                  setFilters((f) => ({
                    ...f,
                    merge_candidates: f.merge_candidates ? undefined : true,
                  }))
                }
                className={cn(
                  "inline-flex items-center rounded-xl border px-3 py-2 text-sm font-medium",
                  filters.merge_candidates
                    ? "border-amber-300 bg-amber-50 text-amber-900"
                    : "border-primary/10 text-secondary hover:bg-slate-50"
                )}
              >
                Merge queue
              </button>
              <button
                type="button"
                onClick={() =>
                  setFilters((f) => ({
                    ...f,
                    sla_breached: f.sla_breached ? undefined : true,
                  }))
                }
                className={cn(
                  "inline-flex items-center rounded-xl border px-3 py-2 text-sm font-medium",
                  filters.sla_breached
                    ? "border-red-300 bg-red-50 text-red-900"
                    : "border-primary/10 text-secondary hover:bg-slate-50"
                )}
              >
                SLA breach
              </button>
              <button
                type="button"
                onClick={() =>
                  setFilters((f) => ({
                    ...f,
                    unassigned: f.unassigned ? undefined : true,
                  }))
                }
                className={cn(
                  "inline-flex items-center rounded-xl border px-3 py-2 text-sm font-medium",
                  filters.unassigned
                    ? "border-sky-300 bg-sky-50 text-sky-900"
                    : "border-primary/10 text-secondary hover:bg-slate-50"
                )}
              >
                Unassigned
              </button>
              <Link
                href="/leads/pipeline"
                className="inline-flex items-center rounded-xl border border-primary/10 px-3 py-2 text-sm font-medium text-secondary hover:bg-slate-50"
              >
                Pipeline
              </Link>
              <Link
                href="/leads/calendar"
                className="inline-flex items-center rounded-xl border border-primary/10 px-3 py-2 text-sm font-medium text-secondary hover:bg-slate-50"
              >
                Calendar
              </Link>
            </>
          ) : null}
          <Button variant="outline" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        </div>
      </div>

      {showCapture ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-lg space-y-3 rounded-2xl bg-white p-5 shadow-xl">
            <h2 className="text-lg font-semibold text-primary">Manual lead capture</h2>
            <p className="text-sm text-muted">
              Call, SMS, WhatsApp, or referral — lands on the ingest bus.
            </p>
            {(
              [
                ["company_name", "Company"],
                ["primary_contact_name", "Contact"],
                ["email", "Email"],
                ["phone", "Phone"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="block text-sm">
                <span className="mb-1 block font-medium">{label}</span>
                <input
                  className="w-full rounded-xl border border-primary/10 px-3 py-2"
                  value={capture[key]}
                  onChange={(e) => setCapture((c) => ({ ...c, [key]: e.target.value }))}
                />
              </label>
            ))}
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Channel</span>
              <select
                className="w-full rounded-xl border border-primary/10 px-3 py-2"
                value={capture.channel}
                onChange={(e) =>
                  setCapture((c) => ({
                    ...c,
                    channel: e.target.value,
                    source: e.target.value,
                  }))
                }
              >
                {["phone_call", "sms", "whatsapp", "merchant_referral", "manual"].map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Notes</span>
              <textarea
                className="w-full rounded-xl border border-primary/10 px-3 py-2"
                rows={3}
                value={capture.internal_notes}
                onChange={(e) => setCapture((c) => ({ ...c, internal_notes: e.target.value }))}
              />
            </label>
            <div className="space-y-2 rounded-xl border border-primary/10 p-3">
              <p className="text-xs font-medium text-muted">Consent (phone or email required)</p>
              {(
                [
                  ["consent_marketing", "Marketing email"],
                  ["consent_sms", "SMS"],
                  ["consent_whatsapp", "WhatsApp"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={capture[key]}
                    onChange={(e) => setCapture((c) => ({ ...c, [key]: e.target.checked }))}
                  />
                  {label}
                </label>
              ))}
            </div>
            {captureError ? <p className="text-sm text-red-600">{captureError}</p> : null}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setShowCapture(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                disabled={
                  captureBusy ||
                  !capture.company_name.trim() ||
                  (!capture.email.trim() && !capture.phone.trim())
                }
                onClick={() => {
                  void (async () => {
                    setCaptureBusy(true);
                    setCaptureError("");
                    try {
                      if (!capture.email.trim() && !capture.phone.trim()) {
                        setCaptureError("Email or phone is required");
                        return;
                      }
                      const token = await getApiToken();
                      await leadsApi.create(token, {
                        company_name: capture.company_name.trim(),
                        primary_contact_name: capture.primary_contact_name || undefined,
                        email: capture.email || undefined,
                        phone: capture.phone || undefined,
                        source: capture.source,
                        channel: capture.channel,
                        internal_notes: capture.internal_notes || undefined,
                        consent: {
                          marketing: capture.consent_marketing,
                          sms: capture.consent_sms,
                          whatsapp: capture.consent_whatsapp,
                        },
                      });
                      setShowCapture(false);
                      void refetch();
                    } catch (err) {
                      setCaptureError(err instanceof Error ? err.message : "Create failed");
                    } finally {
                      setCaptureBusy(false);
                    }
                  })();
                }}
              >
                {captureBusy ? "Saving…" : "Create lead"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {metrics && !isDriverInbox ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-primary/10 bg-white p-4">
            <p className="text-xs font-medium text-muted">Ingest (30d)</p>
            <p className="mt-1 text-2xl font-semibold text-primary">{metrics.ingest.total}</p>
          </div>
          <div className="rounded-2xl border border-primary/10 bg-white p-4">
            <p className="text-xs font-medium text-muted">Convert rate</p>
            <p className="mt-1 text-2xl font-semibold text-primary">
              {metrics.leads.conversion_rate}%
            </p>
          </div>
          <div className="rounded-2xl border border-primary/10 bg-white p-4">
            <p className="text-xs font-medium text-muted">SLA breached</p>
            <p className="mt-1 text-2xl font-semibold text-primary">{metrics.sla.breached_new}</p>
          </div>
          <div className="rounded-2xl border border-primary/10 bg-white p-4">
            <p className="text-xs font-medium text-muted">Meta Lead ID coverage</p>
            <p className="mt-1 text-2xl font-semibold text-primary">
              {metrics.capi.meta_lead_id_coverage_pct == null
                ? "—"
                : `${metrics.capi.meta_lead_id_coverage_pct}%`}
            </p>
          </div>
        </div>
      ) : null}

      <div className="rounded-2xl border border-primary/10 bg-white p-4">
        {!isDriverInbox ? (
          <div className="mb-3 flex flex-wrap gap-1.5">
            <button
              type="button"
              onClick={() => setFilters((f) => ({ ...f, source: undefined, channel: undefined }))}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs font-medium",
                !filters.source && !filters.channel
                  ? "border-secondary bg-secondary/10 text-secondary"
                  : "border-primary/10 text-muted hover:bg-slate-50"
              )}
            >
              All sources
            </button>
            {LEAD_CHANNELS.map((ch) => (
              <button
                key={ch}
                type="button"
                onClick={() =>
                  setFilters((f) => ({
                    ...f,
                    channel: f.channel === ch ? undefined : ch,
                    source: undefined,
                  }))
                }
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs font-medium capitalize",
                  filters.channel === ch
                    ? "border-secondary bg-secondary/10 text-secondary"
                    : "border-primary/10 text-muted hover:bg-slate-50"
                )}
              >
                {ch.replace(/_/g, " ")}
              </button>
            ))}
          </div>
        ) : null}
        <div className="mb-4 flex flex-wrap gap-2">
          <input
            type="search"
            placeholder="Search name, email, company…"
            value={filters.search ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
            className="min-w-[220px] flex-1 rounded-xl border border-primary/10 px-3 py-2 text-sm"
          />
          <select
            value={filters.status ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {LEAD_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <select
            value={filters.decision_status ?? ""}
            onChange={(e) =>
              setFilters((f) => ({ ...f, decision_status: e.target.value || undefined }))
            }
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All decisions</option>
            {LEAD_DECISION_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <select
            value={filters.channel ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, channel: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All channels</option>
            {LEAD_CHANNELS.map((s) => (
              <option key={s} value={s}>
                {sourceLabel(s)}
              </option>
            ))}
          </select>
          <select
            value={filters.intent_type ?? ""}
            onChange={(e) =>
              setFilters((f) => ({ ...f, intent_type: e.target.value || undefined }))
            }
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All intents</option>
            {LEAD_INTENT_TYPES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <select
            value={filters.priority ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, priority: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All priorities</option>
            {LEAD_PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <select
            value={filters.source ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, source: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All sources</option>
            {LEAD_SOURCES.map((s) => (
              <option key={s} value={s}>
                {sourceLabel(s)}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : rows.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted">
            {isDriverInbox ? "No driver partner leads yet." : "No merchant leads yet."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-primary/10 text-xs uppercase tracking-wide text-muted">
                  <th className="px-3 py-2 font-medium">When</th>
                  <th className="px-3 py-2 font-medium">Contact</th>
                  <th className="px-3 py-2 font-medium">Channel</th>
                  <th className="px-3 py-2 font-medium">Decision</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Score</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((lead) => {
                  const intent = leadIntent(lead);
                  const form = leadForm(lead);
                  return (
                    <tr key={lead.id} className="border-b border-primary/5 hover:bg-slate-50">
                      <td className="px-3 py-3 text-muted whitespace-nowrap">
                        {formatWhen(lead.created_at)}
                      </td>
                      <td className="px-3 py-3">
                        <Link
                          href={`/leads/${lead.id}`}
                          className="font-medium text-secondary hover:underline"
                        >
                          {lead.company_name}
                        </Link>
                        <p className="text-xs text-muted">
                          {lead.primary_contact_name ?? "—"}
                          {lead.email ? ` · ${lead.email}` : ""}
                        </p>
                        {(intent || lead.intent_type) && (
                          <p className="mt-0.5 text-xs capitalize text-primary/70">
                            Intent: {lead.intent_type ?? intent}
                          </p>
                        )}
                        {lead.merge_candidate_of ? (
                          <div className="mt-1 flex flex-wrap items-center gap-2">
                            <p className="text-xs text-amber-700">
                              Merge candidate of{" "}
                              <Link
                                href={`/leads/${lead.merge_candidate_of}`}
                                className="underline"
                              >
                                {lead.merge_candidate_of.slice(0, 8)}…
                              </Link>
                            </p>
                            <button
                              type="button"
                              className="text-xs font-medium text-emerald-700 hover:underline"
                              onClick={() => {
                                void (async () => {
                                  const token = await getApiToken();
                                  await leadsApi.resolveMerge(token, lead.id, "accept");
                                  void refetch();
                                })();
                              }}
                            >
                              Accept merge
                            </button>
                            <button
                              type="button"
                              className="text-xs font-medium text-muted hover:underline"
                              onClick={() => {
                                void (async () => {
                                  const token = await getApiToken();
                                  await leadsApi.resolveMerge(token, lead.id, "reject");
                                  void refetch();
                                })();
                              }}
                            >
                              Keep separate
                            </button>
                          </div>
                        ) : null}
                      </td>
                      <td className="px-3 py-3">
                        <span className="text-primary">
                          {sourceLabel(lead.channel ?? lead.source)}
                        </span>
                        <p className="mt-0.5 text-xs text-muted">{sourceLabel(lead.source)}</p>
                        {form && (
                          <p className="mt-0.5 text-xs text-muted capitalize">Form: {form}</p>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <Badge tone={DECISION_TONES[lead.decision_status ?? "new"] ?? "slate"}>
                          {(lead.decision_status ?? "new").replace(/_/g, " ")}
                        </Badge>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex flex-wrap gap-1">
                          <Badge tone={STATUS_TONES[lead.status] ?? "slate"}>{lead.status}</Badge>
                          <Badge tone={PRIORITY_TONES[lead.priority] ?? "slate"}>
                            {lead.priority}
                          </Badge>
                        </div>
                      </td>
                      <td
                        className={cn(
                          "px-3 py-3 font-mono",
                          lead.lead_score >= 30 && "font-semibold"
                        )}
                      >
                        {lead.lead_score}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {referralCredits.length > 0 ? (
        <div className="mt-6 rounded-xl border border-primary/10 bg-white p-4">
          <h2 className="text-sm font-semibold text-primary">Referral credits</h2>
          <p className="mt-1 text-xs text-muted">
            Merchant referral rewards pending or granted from converted referred leads.
          </p>
          <ul className="mt-3 divide-y divide-primary/5 text-sm">
            {referralCredits.slice(0, 8).map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span className="text-muted">
                  <Link href={`/leads/${c.lead_id}`} className="text-secondary hover:underline">
                    Lead
                  </Link>
                  {" · "}
                  {(c.amount_cents / 100).toLocaleString(undefined, {
                    style: "currency",
                    currency: (c.currency || "CAD").toUpperCase(),
                  })}
                </span>
                <Badge tone={c.status === "granted" ? "green" : "amber"}>{c.status}</Badge>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </AdminPage>
  );
}
