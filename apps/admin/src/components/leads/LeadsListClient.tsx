"use client";

import Link from "next/link";
import { useCallback, useDeferredValue, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
import LeadBulkBar from "@/components/leads/LeadBulkBar";
import LeadSavedViews from "@/components/leads/LeadSavedViews";
import LeadRow from "@/components/leads/LeadRow";
import {
  Disclosure,
  EmptyState,
  InboxSkeleton,
  Kbd,
  LeadSpeedStrip,
  MoreMenu,
  useTriageKeys,
} from "@/components/leads/LeadDeskBits";
import { useNow } from "@/components/leads/LeadInboxBits";
import {
  LEAD_CHANNELS,
  LEAD_DECISION_STATUSES,
  LEAD_INTENT_TYPES,
  LEAD_PRIORITIES,
  LEAD_STATUSES,
  leadsApi,
  LEAD_SOURCES,
  type LeadFilters,
} from "@/lib/leads";

function sourceLabel(source: string): string {
  if (source === DRIVER_LEAD_SOURCE) return "driver partner";
  return source.replace(/_/g, " ");
}

const VIEW_TABS = [
  { key: "now", label: "Now" },
  { key: "waiting", label: "Waiting" },
  { key: "buyers", label: "All" },
] as const;

export default function LeadsListClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const searchParams = useSearchParams();
  const sourceFromUrl = searchParams.get("source") ?? undefined;
  const priorityFromUrl = searchParams.get("priority") ?? undefined;
  const statusFromUrl = searchParams.get("status") ?? undefined;
  const hasPhoneFromUrl = searchParams.get("has_phone");
  const viewFromUrl = searchParams.get("view") === "drivers" ? "drivers" : undefined;
  const isDriverInbox = sourceFromUrl === DRIVER_LEAD_SOURCE || viewFromUrl === "drivers";
  const inboxTitle = isDriverInbox ? "Driver applicants" : "Inbox";
  const inboxSubtitle = isDriverInbox
    ? "Vehicle partner applications and driver sign-ups — kept out of the sales inbox"
    : sourceFromUrl === WEBSITE_CONTACT_LEAD_SOURCE
      ? "Website /contact inquiries"
      : sourceFromUrl === WEBSITE_NEWSLETTER_LEAD_SOURCE
        ? "Blog + footer newsletter subscriptions"
        : sourceFromUrl === "vendor_import"
          ? "Outbound vendor call queue"
          : "Every lead, one place. Reply in under 5 minutes.";
  const [filters, setFilters] = useState<LeadFilters>(() => {
    const base: LeadFilters = { sort: "smart" };
    // Driver applicants live in their own view; the sales inbox hides them.
    base.view =
      viewFromUrl ??
      (sourceFromUrl === DRIVER_LEAD_SOURCE ? undefined : sourceFromUrl ? "buyers" : "now");
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
        view: viewFromUrl ?? (sourceFromUrl === DRIVER_LEAD_SOURCE ? undefined : (f.view ?? "now")),
      };
      return next;
    });
  }, [sourceFromUrl, priorityFromUrl, statusFromUrl, hasPhoneFromUrl, viewFromUrl]);

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
        limit: listFilters.limit ?? 25,
        offset: 0,
      }),
  });
  const rows = page?.items ?? [];
  const total = page?.total ?? 0;
  const [extra, setExtra] = useState<typeof rows>([]);
  const [loadOffset, setLoadOffset] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  const filtersKey = JSON.stringify({ ...listFilters, offset: undefined, limit: undefined });
  useEffect(() => {
    setExtra([]);
    setLoadOffset(0);
  }, [filtersKey]);

  const allRows = [...rows, ...extra];
  const canLoadMore = allRows.length < total;
  const now = useNow();
  const [selected, setSelected] = useState<string[]>([]);
  const [exporting, setExporting] = useState(false);
  const allSelected = allRows.length > 0 && allRows.every((r) => selected.includes(r.id));
  const toggle = (id: string) =>
    setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));

  const downloadCsv = async (ids?: string[]) => {
    setExporting(true);
    try {
      const blob = await leadsApi.exportCsv(await getApiToken(), listFilters, ids);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `porterchain-leads-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  const { data: referralCredits = [] } = useQuery({
    queryKey: ["lead-referral-credits"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.referralCredits(await getApiToken()),
  });

  const router = useRouter();
  const searchRef = useRef<HTMLInputElement>(null);
  const nextLead = isDriverInbox
    ? undefined
    : (allRows.find((r) => r.awaiting_reply) ?? allRows.find((r) => r.status === "new"));
  const currentView = filters.view ?? "buyers";
  const activeFilterCount = [
    filters.status,
    filters.decision_status,
    filters.channel,
    filters.intent_type,
    filters.priority,
    filters.source,
  ].filter(Boolean).length;
  const rowIds = allRows.map((r) => r.id).join(",");
  const openAt = useCallback(
    (i: number) => {
      const id = rowIds.split(",")[i];
      if (id) router.push(`/leads/${id}`);
    },
    [rowIds, router]
  );
  const toggleAt = useCallback(
    (i: number) => {
      const id = rowIds.split(",")[i];
      if (id) setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
    },
    [rowIds]
  );
  const cursor = useTriageKeys({
    count: allRows.length,
    searchRef,
    onOpen: openAt,
    onToggle: toggleAt,
  });

  return (
    <AdminPage>
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-secondary">Sales</p>
          <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-primary sm:text-4xl">
            {inboxTitle}
          </h1>
          <p className="mt-1 text-sm text-slate-600">{inboxSubtitle}</p>
        </div>
        <div className="flex items-center gap-2">
          {nextLead ? (
            <Link
              href={`/leads/${nextLead.id}`}
              className="inline-flex items-center rounded-full bg-secondary px-5 py-2.5 text-sm font-bold text-white shadow-sm hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary"
            >
              Reply to next lead
            </Link>
          ) : null}
          <MoreMenu>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Views
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(
                [
                  { href: "/leads", label: "All", source: undefined },
                  {
                    href: "/leads?source=website_business",
                    label: "Merchant",
                    source: "website_business",
                  },
                  {
                    href: "/leads?view=drivers",
                    label: "Driver applicants",
                    source: "__drivers__",
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
                    : chip.source === "__drivers__"
                      ? viewFromUrl === "drivers"
                      : !viewFromUrl && (sourceFromUrl ?? undefined) === chip.source;
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
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Actions
            </p>
            <div className="flex flex-wrap items-center gap-2">
              {!isDriverInbox ? (
                <>
                  <button
                    type="button"
                    onClick={async () => {
                      await leadsApi.rescore(await getApiToken());
                      void refetch();
                    }}
                    className="inline-flex items-center rounded-xl border border-primary/15 px-3 py-2 text-sm font-medium text-primary hover:bg-slate-50"
                  >
                    Rescore open leads
                  </button>
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
                  <Link
                    href="/leads/attribution"
                    className="inline-flex items-center rounded-xl border border-primary/10 px-3 py-2 text-sm font-medium text-secondary hover:bg-slate-50"
                  >
                    Attribution
                  </Link>
                </>
              ) : null}
              <Button variant="outline" onClick={() => void downloadCsv()} disabled={exporting}>
                {exporting ? "Exporting…" : "Export CSV"}
              </Button>
              <Button variant="outline" onClick={() => void refetch()}>
                <RefreshCw className="h-4 w-4" /> Refresh
              </Button>
            </div>
          </MoreMenu>
        </div>
      </header>

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

      {!isDriverInbox ? <LeadSpeedStrip /> : null}

      <div className="rounded-3xl border border-primary/10 bg-white p-4 sm:p-6">
        <div className="mb-2 flex flex-wrap items-center gap-3">
          {!isDriverInbox ? (
            <div
              role="tablist"
              aria-label="Inbox view"
              className="flex rounded-full bg-slate-100 p-1"
            >
              {VIEW_TABS.map((t) => (
                <button
                  key={t.key}
                  type="button"
                  role="tab"
                  aria-selected={currentView === t.key}
                  onClick={() => {
                    setSelected([]);
                    setFilters((f) => ({
                      ...f,
                      view: t.key,
                      awaiting_reply: undefined,
                      priority: undefined,
                      status: undefined,
                    }));
                  }}
                  className={cn(
                    "rounded-full px-4 py-1.5 text-sm font-bold",
                    currentView === t.key
                      ? "bg-white text-primary shadow-sm"
                      : "text-slate-600 hover:text-primary"
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>
          ) : null}
          <input
            ref={searchRef}
            type="search"
            placeholder="Search…  /"
            aria-label="Search leads (press / to focus)"
            value={filters.search ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
            className="min-w-0 flex-1 basis-40 rounded-full border border-primary/15 bg-white px-4 py-2 text-sm text-primary placeholder:text-slate-500 focus:border-secondary focus:outline-none"
          />
        </div>
        <div className="mb-3">
          <Disclosure label="Filters" count={activeFilterCount}>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Saved views
            </p>
            <LeadSavedViews
              filters={filters}
              onApply={(next) => {
                setSelected([]);
                setFilters(next);
              }}
            />
            {!isDriverInbox ? (
              <div className="mb-3 flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() =>
                    setFilters((f) => ({ ...f, source: undefined, channel: undefined }))
                  }
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
                onChange={(e) =>
                  setFilters((f) => ({ ...f, channel: e.target.value || undefined }))
                }
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
                onChange={(e) =>
                  setFilters((f) => ({ ...f, priority: e.target.value || undefined }))
                }
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
          </Disclosure>
        </div>

        <LeadBulkBar
          selected={selected}
          getToken={getApiToken}
          onDone={() => void refetch()}
          onClear={() => setSelected([])}
          onExportSelected={() => void downloadCsv(selected)}
        />
        {isLoading ? (
          <InboxSkeleton />
        ) : allRows.length === 0 ? (
          <EmptyState
            title={
              isDriverInbox
                ? "No driver applicants yet"
                : currentView === "now"
                  ? "Inbox zero"
                  : currentView === "waiting"
                    ? "Nobody to chase"
                    : "No leads match"
            }
            hint={
              isDriverInbox
                ? "Vehicle-partner applications and driver sign-ups land here."
                : currentView === "now"
                  ? "Nobody is waiting on you. New forms, WhatsApp, email and sign-ups appear here the moment they arrive."
                  : currentView === "waiting"
                    ? "Leads you replied to or quoted show here until they answer."
                    : "Try clearing filters or search."
            }
            action={
              !isDriverInbox && currentView !== "buyers" ? (
                <Button
                  variant="outline"
                  onClick={() => setFilters((f) => ({ ...f, view: "buyers" }))}
                >
                  See all leads
                </Button>
              ) : null
            }
          />
        ) : (
          <div>
            <p className="sr-only" aria-live="polite">
              {total} leads in inbox, showing {allRows.length}
            </p>
            {!isDriverInbox ? (
              <div className="hidden items-center gap-3 border-b border-primary/5 pb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 md:flex">
                <input
                  type="checkbox"
                  className="h-4 w-4"
                  aria-label="Select all leads on screen"
                  checked={allSelected}
                  onChange={() => setSelected(allSelected ? [] : allRows.map((r) => r.id))}
                />
                <span className="ml-12 flex-1">Lead</span>
                <span className="hidden w-20 sm:block">Status</span>
                <span className="w-24 text-right">Waiting</span>
                <span className="w-10 text-right">Score</span>
              </div>
            ) : null}
            <ul className="divide-y divide-primary/5" aria-label="Lead inbox">
              {allRows.map((lead, idx) => (
                <LeadRow
                  key={lead.id}
                  lead={lead}
                  now={now}
                  active={cursor === idx}
                  selected={selected.includes(lead.id)}
                  onToggle={() => toggle(lead.id)}
                />
              ))}
            </ul>
            {canLoadMore ? (
              <div className="mt-4 flex justify-center">
                <Button
                  variant="outline"
                  aria-busy={loadingMore}
                  onClick={() => {
                    void (async () => {
                      setLoadingMore(true);
                      try {
                        const nextOffset = (page?.limit ?? 25) + loadOffset;
                        const more = await leadsApi.list(await getApiToken(), {
                          ...listFilters,
                          limit: page?.limit ?? 25,
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

      <p className="hidden text-center text-xs text-slate-500 md:block">
        <Kbd>j</Kbd>/<Kbd>k</Kbd> move · <Kbd>Enter</Kbd> open · <Kbd>x</Kbd> select · <Kbd>/</Kbd>{" "}
        search
      </p>

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
