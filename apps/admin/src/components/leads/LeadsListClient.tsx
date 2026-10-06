"use client";

import Link from "next/link";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useDeferredValue, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Badge, Button } from "@/components/crm/primitives";
import {
  DRIVER_LEAD_SOURCE,
  WEBSITE_CONTACT_LEAD_SOURCE,
  WEBSITE_NEWSLETTER_LEAD_SOURCE,
} from "@/lib/admin-nav";
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
  const priorityFromUrl = searchParams.get("priority") ?? undefined;
  const statusFromUrl = searchParams.get("status") ?? undefined;
  const hasPhoneFromUrl = searchParams.get("has_phone");
  const isDriverInbox = sourceFromUrl === DRIVER_LEAD_SOURCE;
  const inboxTitle = "Lead Workspace";
  const inboxSubtitle = isDriverInbox
    ? "Vehicle partner applications from /vehicle-partner"
    : sourceFromUrl === WEBSITE_CONTACT_LEAD_SOURCE
      ? "Website /contact inquiries"
      : sourceFromUrl === WEBSITE_NEWSLETTER_LEAD_SOURCE
        ? "Blog + footer newsletter subscriptions"
        : sourceFromUrl === "vendor_import"
          ? "Outbound vendor call queue"
          : "Merchant, retail, driver, and newsletter inbox";
  const [filters, setFilters] = useState<LeadFilters>(() => {
    const base: LeadFilters = { sort: "smart" };
    if (sourceFromUrl) base.source = sourceFromUrl;
    if (priorityFromUrl) base.priority = priorityFromUrl;
    if (statusFromUrl) base.status = statusFromUrl;
    if (hasPhoneFromUrl === "true") base.has_phone = true;
    return base;
  });
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
    legal_basis: "consent" as "consent" | "legitimate_interest" | "contract",
  });

  useEffect(() => {
    setFilters((f) => {
      const next: LeadFilters = {
        ...f,
        source: sourceFromUrl,
        priority: priorityFromUrl,
        status: statusFromUrl ?? f.status,
        has_phone:
          hasPhoneFromUrl === "true" ? true : hasPhoneFromUrl === "false" ? false : undefined,
      };
      return next;
    });
  }, [sourceFromUrl, priorityFromUrl, statusFromUrl, hasPhoneFromUrl]);

  const deferredSearch = useDeferredValue(filters.search);
  const listFilters = { ...filters, search: deferredSearch };

  const {
    data: page,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["leads", JSON.stringify({ ...listFilters, offset: undefined })],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () =>
      leadsApi.list(await getApiToken(), {
        ...listFilters,
        limit: listFilters.limit ?? 50,
        offset: 0,
      }),
  });
  const rows = page?.items ?? [];
  const total = page?.total ?? 0;
  const [extra, setExtra] = useState<typeof rows>([]);
  const [loadOffset, setLoadOffset] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    setExtra([]);
    setLoadOffset(0);
  }, [JSON.stringify({ ...listFilters, offset: undefined, limit: undefined })]);

  const allRows = [...rows, ...extra];
  const canLoadMore = allRows.length < total;

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
          <h1 className="text-2xl font-bold text-primary">{inboxTitle}</h1>
          <p className="text-sm text-muted">{inboxSubtitle}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {(
              [
                { href: "/leads", label: "All", source: undefined },
                {
                  href: "/leads?source=website_business",
                  label: "Merchant",
                  source: "website_business",
                },
                {
                  href: `/leads?source=${DRIVER_LEAD_SOURCE}`,
                  label: "Driver",
                  source: DRIVER_LEAD_SOURCE,
                },
                {
                  href: `/leads?source=${WEBSITE_CONTACT_LEAD_SOURCE}`,
                  label: "Contact",
                  source: WEBSITE_CONTACT_LEAD_SOURCE,
                },
                {
                  href: `/leads?source=${WEBSITE_NEWSLETTER_LEAD_SOURCE}`,
                  label: "Newsletter",
                  source: WEBSITE_NEWSLETTER_LEAD_SOURCE,
                },
                {
                  href: "/leads?source=vendor_import&priority=high&has_phone=true&status=new",
                  label: "Call queue",
                  source: "vendor_import",
                },
                {
                  href: "/leads/today",
                  label: "Today",
                  source: "__today__",
                },
                {
                  href: "/leads/agent",
                  label: "Lead Agent",
                  source: "__agent__",
                },
              ] as const
            ).map((chip) => {
              const active =
                chip.source === "__today__" || chip.source === "__agent__"
                  ? false
                  : (sourceFromUrl ?? undefined) === chip.source;
              return (
                <Link
                  key={chip.label}
                  href={chip.href}
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-xs font-medium",
                    active
                      ? "border-secondary bg-secondary/10 text-secondary"
                      : chip.source === "__agent__"
                        ? "border-secondary/40 bg-secondary/5 text-secondary hover:bg-secondary/10"
                        : "border-primary/10 text-muted hover:bg-slate-50"
                  )}
                >
                  {chip.label}
                </Link>
              );
            })}
            <Link
              href="/settings?section=lead_ingest"
              className="rounded-full border border-primary/10 px-2.5 py-1 text-xs font-medium text-muted hover:bg-slate-50"
            >
              Ingest settings
            </Link>
            <button
              type="button"
              onClick={() =>
                setFilters((f) => ({
                  ...f,
                  sort: (f.sort ?? "smart") === "smart" ? "created_at" : "smart",
                }))
              }
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs font-medium",
                (filters.sort ?? "smart") === "smart"
                  ? "border-secondary bg-secondary/10 text-secondary"
                  : "border-primary/10 text-muted hover:bg-slate-50"
              )}
              title="SLA breached → priority → score → newest"
              aria-label="Toggle smart triage sort"
              aria-pressed={(filters.sort ?? "smart") === "smart"}
            >
              {(filters.sort ?? "smart") === "smart" ? "Smart triage" : "Newest first"}
            </button>
            <button
              type="button"
              onClick={() =>
                setFilters((f) => ({
                  ...f,
                  status: f.status === "archived" ? undefined : "archived",
                  include_archived: f.status === "archived" ? undefined : true,
                }))
              }
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary",
                filters.status === "archived"
                  ? "border-slate-400 bg-slate-100 text-slate-800"
                  : "border-primary/10 text-muted hover:bg-slate-50"
              )}
              aria-label="Toggle archived leads"
              aria-pressed={filters.status === "archived"}
            >
              Archived
            </button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {!isDriverInbox ? (
            <>
              <Link
                href="/leads/agent"
                className="inline-flex items-center rounded-xl bg-primary px-3 py-2 text-sm font-medium text-white hover:opacity-90"
                aria-label="Open Lead Agent activity"
              >
                Lead Agent
              </Link>
              <button
                type="button"
                onClick={() => setShowCapture(true)}
                className="inline-flex items-center rounded-xl border border-primary/10 px-3 py-2 text-sm font-medium text-secondary hover:bg-slate-50"
                aria-label="Add lead"
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
                  "inline-flex items-center rounded-xl border px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary",
                  filters.merge_candidates
                    ? "border-amber-300 bg-amber-50 text-amber-900"
                    : "border-primary/10 text-secondary hover:bg-slate-50"
                )}
                aria-label="Toggle merge candidate queue"
                aria-pressed={Boolean(filters.merge_candidates)}
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
                  "inline-flex items-center rounded-xl border px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary",
                  filters.sla_breached
                    ? "border-red-300 bg-red-50 text-red-900"
                    : "border-primary/10 text-secondary hover:bg-slate-50"
                )}
                aria-label="Toggle SLA-breached leads"
                aria-pressed={Boolean(filters.sla_breached)}
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
                  "inline-flex items-center rounded-xl border px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary",
                  filters.unassigned
                    ? "border-sky-300 bg-sky-50 text-sky-900"
                    : "border-primary/10 text-secondary hover:bg-slate-50"
                )}
                aria-label="Toggle unassigned leads"
                aria-pressed={Boolean(filters.unassigned)}
              >
                Unassigned
              </button>
              <button
                type="button"
                onClick={() =>
                  setFilters((f) => ({
                    ...f,
                    has_open_draft: f.has_open_draft ? undefined : true,
                  }))
                }
                className={cn(
                  "inline-flex items-center rounded-xl border px-3 py-2 text-sm font-medium",
                  filters.has_open_draft
                    ? "border-violet-300 bg-violet-50 text-violet-900"
                    : "border-primary/10 text-secondary hover:bg-slate-50"
                )}
              >
                Open draft
              </button>
              <button
                type="button"
                onClick={() =>
                  setFilters((f) => ({
                    ...f,
                    nurture_scheduled: f.nurture_scheduled ? undefined : true,
                  }))
                }
                className={cn(
                  "inline-flex items-center rounded-xl border px-3 py-2 text-sm font-medium",
                  filters.nurture_scheduled
                    ? "border-teal-300 bg-teal-50 text-teal-900"
                    : "border-primary/10 text-secondary hover:bg-slate-50"
                )}
              >
                Nurture
              </button>
              <button
                type="button"
                onClick={() =>
                  setFilters((f) => ({
                    ...f,
                    has_abandoned: f.has_abandoned ? undefined : true,
                  }))
                }
                className={cn(
                  "inline-flex items-center rounded-xl border px-3 py-2 text-sm font-medium",
                  filters.has_abandoned
                    ? "border-orange-300 bg-orange-50 text-orange-900"
                    : "border-primary/10 text-secondary hover:bg-slate-50"
                )}
              >
                Abandoned checkout
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
              <p className="text-xs font-medium text-muted">
                Consent (phone or email required). Marketing needs a legal basis.
              </p>
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
              {capture.consent_marketing ? (
                <label className="block text-sm">
                  <span className="mb-1 block font-medium">Legal basis</span>
                  <select
                    className="w-full rounded-xl border border-primary/10 px-3 py-2"
                    value={capture.legal_basis}
                    onChange={(e) =>
                      setCapture((c) => ({
                        ...c,
                        legal_basis: e.target.value as typeof c.legal_basis,
                      }))
                    }
                  >
                    <option value="consent">Consent (CASL / GDPR Art.6)</option>
                    <option value="legitimate_interest">Legitimate interest</option>
                    <option value="contract">Contract</option>
                  </select>
                </label>
              ) : null}
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
                          ...(capture.consent_marketing
                            ? { legal_basis: capture.legal_basis }
                            : {}),
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
          <div className="flex justify-center py-12" role="status" aria-live="polite">
            <PageSkeleton rows={3} />
            <span className="sr-only">Loading leads</span>
          </div>
        ) : allRows.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted" role="status" aria-live="polite">
            {isDriverInbox ? "No driver partner leads yet." : "No leads yet."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <p className="sr-only" aria-live="polite">
              {total} leads in inbox, showing {allRows.length}
            </p>
            <table className="w-full min-w-[720px] text-left text-sm" aria-label="Lead inbox">
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
                {allRows.map((lead) => {
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
                        <div className="mt-1 flex flex-wrap gap-1">
                          {lead.status === "archived" ? <Badge tone="slate">archived</Badge> : null}
                          {lead.booking_draft_id ? <Badge tone="violet">draft</Badge> : null}
                          {lead.status === "nurturing" ||
                          (lead.tags || []).some((t) =>
                            String(t).toLowerCase().includes("nurture")
                          ) ? (
                            <Badge tone="teal">nurture</Badge>
                          ) : null}
                          {lead.sla_first_response_due_at &&
                          lead.status === "new" &&
                          new Date(lead.sla_first_response_due_at).getTime() < Date.now() ? (
                            <Badge tone="red">SLA</Badge>
                          ) : null}
                        </div>
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
            {canLoadMore ? (
              <div className="mt-4 flex justify-center">
                <Button
                  variant="outline"
                  aria-busy={loadingMore}
                  onClick={() => {
                    void (async () => {
                      setLoadingMore(true);
                      try {
                        const nextOffset = (page?.limit ?? 50) + loadOffset;
                        const more = await leadsApi.list(await getApiToken(), {
                          ...listFilters,
                          limit: page?.limit ?? 50,
                          offset: nextOffset,
                        });
                        setExtra((prev) => [...prev, ...more.items]);
                        setLoadOffset(nextOffset);
                      } finally {
                        setLoadingMore(false);
                      }
                    })();
                  }}
                >
                  {loadingMore ? "Working…" : `Load more (${allRows.length} of ${total})`}
                </Button>
              </div>
            ) : null}
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
