"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Building2, Info, KeyRound, Package, Receipt, Users } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { getSystemLinks } from "@/lib/system-links";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchantStatusLabel } from "@/lib/catalog";
import {
  merchants,
  merchantActionMessage,
  vehicleClassLabel,
  type MerchantDetail,
} from "@/lib/merchants";
import { merchantOps, type MerchantOps } from "@/lib/merchant-ops";
import {
  ACTIVITY_IDS,
  ACTIVITY_PANELS,
  MONEY_IDS,
  MONEY_PANELS,
  PEOPLE_IDS,
  PEOPLE_PANELS,
  parseMerchantTab,
  type ActivityPanel,
  type MoneyPanel,
  type PeoplePanel,
  type Route,
  type TabId,
} from "@/lib/merchant-tabs";
import { EntityAlertsPanel } from "@/components/alerts/EntityAlertsPanel";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { EntityTasks } from "@/components/crm/EntityTasks";
import { money, shortDate, relativeTime, titleCase, dateTime } from "@/lib/crmFormat";
import {
  HealthReasons,
  MerchantHero,
  OwnerSegmentCard,
} from "@/components/merchants/ops/MerchantOpsOverview";
import {
  ActionMenu,
  Dialog,
  Empty,
  Panel,
  Pill,
  PrimaryAction,
  QuietButton,
  SkeletonRows,
} from "@/components/merchants/ops/ui";
import AdminPage from "@/components/layout/AdminPage";

const tabFallback = () => <SkeletonRows rows={3} label="Loading section" />;

const MerchantContactsPanel = dynamic(
  () => import("@/components/merchants/MerchantContactsPanel"),
  { loading: tabFallback }
);
const MerchantLocationsPanel = dynamic(
  () => import("@/components/merchants/MerchantLocationsPanel"),
  { loading: tabFallback }
);
const MerchantPricingPanel = dynamic(() => import("@/components/merchants/MerchantPricingPanel"), {
  loading: tabFallback,
});
const MerchantPrivacyCard = dynamic(() => import("@/components/merchants/MerchantPrivacyCard"), {
  loading: tabFallback,
});
const MerchantStandingOrdersCard = dynamic(
  () => import("@/components/merchants/MerchantStandingOrdersCard"),
  { loading: tabFallback }
);
const MerchantTeamPanel = dynamic(() => import("@/components/merchants/MerchantTeamPanel"), {
  loading: tabFallback,
});
const MerchantIntegrationsTab = dynamic(
  () => import("@/components/merchants/MerchantIntegrationsTab"),
  { loading: tabFallback }
);
const OrdersTab = dynamic(
  () => import("@/components/merchants/MerchantOrdersTab").then((m) => m.OrdersTab),
  { loading: tabFallback }
);
const StatementTab = dynamic(
  () => import("@/components/merchants/MerchantMoneyTabs").then((m) => m.StatementTab),
  { loading: tabFallback }
);
const InvoicesTab = dynamic(
  () => import("@/components/merchants/MerchantMoneyTabs").then((m) => m.InvoicesTab),
  { loading: tabFallback }
);
const CreditNotesTab = dynamic(
  () => import("@/components/merchants/MerchantMoneyTabs").then((m) => m.CreditNotesTab),
  { loading: tabFallback }
);
const ContractsTab = dynamic(
  () => import("@/components/merchants/MerchantMoneyTabs").then((m) => m.ContractsTab),
  { loading: tabFallback }
);
const MerchantCreditCard = dynamic(
  () => import("@/components/merchants/ops/MerchantCreditCard").then((m) => m.MerchantCreditCard),
  { loading: tabFallback }
);
const MerchantQuotePreview = dynamic(
  () =>
    import("@/components/merchants/ops/MerchantQuotePreview").then((m) => m.MerchantQuotePreview),
  { loading: tabFallback }
);
const MerchantDocumentsPanel = dynamic(
  () =>
    import("@/components/merchants/ops/MerchantDocumentsPanel").then(
      (m) => m.MerchantDocumentsPanel
    ),
  { loading: tabFallback }
);
const MerchantSupportPanel = dynamic(
  () =>
    import("@/components/merchants/ops/MerchantSupportPanel").then((m) => m.MerchantSupportPanel),
  { loading: tabFallback }
);
const MerchantChangeHistory = dynamic(
  () =>
    import("@/components/merchants/ops/MerchantChangeHistory").then((m) => m.MerchantChangeHistory),
  { loading: tabFallback }
);
const SettingsTab = dynamic(
  () => import("@/components/merchants/MerchantSettingsTab").then((m) => m.SettingsTab),
  { loading: tabFallback }
);

const TABS: {
  id: TabId;
  label: string;
  short: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { id: "overview", label: "Overview", short: "Overview", icon: Info },
  { id: "orders", label: "Orders & delivery times", short: "Orders", icon: Package },
  { id: "money", label: "Money", short: "Money", icon: Receipt },
  { id: "connections", label: "Connections", short: "Connections", icon: KeyRound },
  { id: "people", label: "People & files", short: "People", icon: Users },
];

type Lifecycle = "approve" | "suspend" | "unsuspend" | "reopen";
const LIFECYCLE_COPY: Record<
  Lifecycle,
  { title: string; body: string; cta: string; danger?: boolean }
> = {
  approve: {
    title: "Approve this merchant?",
    body: "They can book live deliveries right away.",
    cta: "Approve",
  },
  suspend: {
    title: "Suspend this merchant?",
    body: "Portal sign-in and new bookings stop. Open orders still deliver.",
    cta: "Suspend",
    danger: true,
  },
  unsuspend: {
    title: "Unsuspend this merchant?",
    body: "Portal access and booking come back.",
    cta: "Unsuspend",
  },
  reopen: {
    title: "Reopen this account?",
    body: "The account moves back to active.",
    cta: "Reopen",
  },
};

export default function MerchantDetailClient({ id }: { id: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const [route, setRoute] = useState<Route>(() =>
    parseMerchantTab(searchParams.get("tab"), searchParams.get("panel"))
  );
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ text: string; bad?: boolean } | null>(null);
  const [confirm, setConfirm] = useState<Lifecycle | null>(null);
  const merchantPortalBase =
    getSystemLinks().find((l) => l.id === "merchant")?.href ?? "http://localhost:3001";

  const { data: m, error } = useApiData((t) => merchants.detail(t, id), [id, version], {
    key: `merchant-detail-${id}`,
  });
  const { data: ops } = useApiData((t) => merchantOps.overview(t, id), [id, version], {
    key: `merchant-ops-${id}`,
  });
  const refresh = () => setVersion((v) => v + 1);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(t);
  }, [toast]);

  async function copyText(label: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setToast({ text: `${label} copied` });
    } catch {
      setToast({ text: "Could not copy to clipboard", bad: true });
    }
  }

  function go(tab: TabId, panel?: string) {
    const next: Route = { ...route, tab };
    if (tab === "money" && panel && MONEY_IDS.has(panel)) next.money = panel as MoneyPanel;
    if (tab === "people" && panel) {
      if (PEOPLE_IDS.has(panel)) next.people = panel as PeoplePanel;
      if (ACTIVITY_IDS.has(panel)) {
        next.people = "activity";
        next.activity = panel as ActivityPanel;
      }
    }
    setRoute(next);
    const qs = new URLSearchParams({ tab });
    if (tab === "money") qs.set("panel", next.money);
    if (tab === "people") qs.set("panel", next.people === "activity" ? next.activity : next.people);
    router.replace(`/merchants/${id}?${qs.toString()}`, { scroll: false });
    if (tab === "overview") {
      window.setTimeout(
        () =>
          document
            .getElementById("why-score")
            ?.scrollIntoView({ behavior: "smooth", block: "center" }),
        50
      );
    } else {
      window.setTimeout(
        () =>
          document
            .getElementById("merchant-sections")
            ?.scrollIntoView({ behavior: "smooth", block: "start" }),
        50
      );
    }
  }

  useEffect(() => {
    setRoute(parseMerchantTab(searchParams.get("tab"), searchParams.get("panel")));
  }, [searchParams]);

  async function lifecycle(action: Lifecycle) {
    setBusy(true);
    try {
      const token = await getApiToken();
      if (action === "approve") await merchants.approve(token, id);
      else if (action === "suspend") await merchants.suspend(token, id);
      else if (action === "unsuspend") await merchants.unsuspend(token, id);
      else await merchants.reopen(token, id);
      setToast({ text: `${LIFECYCLE_COPY[action].cta} done` });
      refresh();
    } catch (e) {
      setToast({ text: merchantActionMessage(e, `${action} failed`), bad: true });
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  }

  if (error) {
    return (
      <AdminPage>
        <Empty
          icon={<Building2 className="h-6 w-6" aria-hidden />}
          title="Couldn't open this merchant"
          hint={error}
          action={
            <QuietButton onClick={() => router.push("/merchants")}>Back to merchants</QuietButton>
          }
        />
      </AdminPage>
    );
  }
  if (!m) {
    return (
      <AdminPage>
        <SkeletonRows rows={6} label="Loading merchant" />
      </AdminPage>
    );
  }

  const pending = m.status === "PENDING" || m.status === "ONBOARDING";
  const statusPill = ops?.credit.blocked ? (
    <Pill tone="red">Credit hold</Pill>
  ) : m.status !== "ACTIVE" ? (
    <Pill tone={m.status === "SUSPENDED" ? "red" : "amber"}>
      {m.status_label || merchantStatusLabel(m.status)}
    </Pill>
  ) : null;

  const menu = [
    ...(m.status === "ACTIVE"
      ? [{ label: "Suspend", tone: "danger" as const, onSelect: () => setConfirm("suspend") }]
      : []),
    ...(m.status === "SUSPENDED"
      ? [{ label: "Unsuspend", onSelect: () => setConfirm("unsuspend") }]
      : []),
    ...(m.status === "CLOSED" ? [{ label: "Reopen", onSelect: () => setConfirm("reopen") }] : []),
    {
      label: "Open merchant portal",
      onSelect: () => window.open(merchantPortalBase, "_blank", "noopener"),
    },
    { label: "Copy portal URL", onSelect: () => void copyText("Portal URL", merchantPortalBase) },
    { label: "Copy merchant ID", onSelect: () => void copyText("Merchant ID", m.id) },
    {
      label: "COD / Connect",
      onSelect: () => window.open(`${merchantPortalBase}/billing?tab=cod`, "_blank", "noopener"),
    },
    { label: "Booking drafts", onSelect: () => router.push(`/booking-drafts?merchant_id=${m.id}`) },
    ...(m.website
      ? [{ label: "Website", onSelect: () => window.open(m.website!, "_blank", "noopener") }]
      : []),
    { label: "Privacy · export or erase", onSelect: () => go("people", "privacy") },
  ];
  const lc = confirm ? LIFECYCLE_COPY[confirm] : null;

  return (
    <AdminPage>
      <Link
        href="/merchants"
        className="inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-primary"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden /> Merchants
      </Link>

      <section
        className={cn(
          "min-w-0 rounded-[2rem] border border-primary/10 bg-white",
          route.tab === "overview" ? "space-y-7 p-5 sm:p-8" : "p-4 sm:p-5"
        )}
      >
        <header className="flex items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-primary/[0.05] text-primary sm:h-14 sm:w-14">
            {m.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={m.logo_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <Building2 className="h-6 w-6" aria-hidden />
            )}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-semibold tracking-[0.18em] text-secondary uppercase">
              {ops ? ops.segment.label : m.industry || "Merchant"}
              {ops ? ` · ${ops.owner.name ?? "No owner"}` : ""}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
              <h1
                className={cn(
                  "min-w-0 text-2xl font-extrabold tracking-tight text-primary",
                  route.tab === "overview" && "sm:text-4xl"
                )}
              >
                {m.company_name}
              </h1>
              {statusPill}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {pending ? (
              <PrimaryAction
                onClick={() => setConfirm("approve")}
                disabled={busy}
                className="hidden sm:inline-flex"
              >
                Approve
              </PrimaryAction>
            ) : null}
            <ActionMenu
              items={
                pending
                  ? [{ label: "Approve", onSelect: () => setConfirm("approve") }, ...menu]
                  : menu
              }
            />
          </div>
        </header>
        {route.tab === "overview" ? (
          <MerchantHero
            ops={ops ?? undefined}
            revenue30dCents={m.metrics.monthly_revenue_cents}
            orders30d={m.metrics.monthly_orders}
            onGo={(t, p) => go(t as TabId, p)}
          />
        ) : null}
      </section>

      {toast && (
        <p
          role="status"
          className={cn(
            "fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full px-5 py-3 text-sm font-semibold shadow-xl",
            toast.bad ? "bg-red-700 text-white" : "bg-primary text-white"
          )}
        >
          {toast.text}
        </p>
      )}

      <nav
        id="merchant-sections"
        className="sticky top-0 z-10 -mx-1 scroll-mt-4 bg-gray-bg/90 px-1 py-2 backdrop-blur"
        aria-label="Merchant sections"
      >
        <div className="ops-tab-rail gap-1 border-b border-primary/10" role="tablist">
          {TABS.map(({ id: tid, label, short, icon: Icon }) => (
            <button
              key={tid}
              type="button"
              role="tab"
              aria-selected={route.tab === tid}
              onClick={() => go(tid)}
              className={cn(
                "-mb-px flex min-h-11 shrink-0 items-center gap-2 border-b-2 px-3 text-sm font-semibold whitespace-nowrap",
                route.tab === tid
                  ? "border-secondary text-primary"
                  : "border-transparent text-slate-600 hover:text-primary"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              <span className="sm:hidden">{short}</span>
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>
      </nav>

      <div className="min-w-0">
        {route.tab === "overview" && (
          <div className="space-y-6">
            {m.portal_ready === false && (
              <div className="flex flex-col gap-3 rounded-3xl bg-amber-50 px-5 py-4 text-sm text-amber-950 sm:flex-row sm:items-center">
                <p className="flex-1">
                  Not portal-ready yet. Invite the owner and activate the seat.
                </p>
                <QuietButton onClick={() => go("people", "team")}>Open team</QuietButton>
              </div>
            )}
            {ops ? (
              <div className="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
                <HealthReasons ops={ops} />
                <div className="space-y-6">
                  <OwnerSegmentCard ops={ops} onSaved={refresh} />
                  <AtAGlance m={m} onGoto={go} />
                </div>
              </div>
            ) : (
              <SkeletonRows rows={4} label="Loading health" />
            )}
            <BusinessDetails m={m} />
            <EntityAlertsPanel
              recipientType="merchant"
              recipientId={m.id}
              careHref={`/support?merchant_id=${m.id}`}
            />
            <LazyAnalytics id={m.id} />
            <MerchantChangeHistory id={id} version={version} />
          </div>
        )}
        {route.tab === "orders" && (
          <div className="space-y-6">
            {ops && <DeliveryTimes ops={ops} />}
            <OrdersTab id={id} />
            <MerchantStandingOrdersCard id={id} />
          </div>
        )}
        {route.tab === "money" && (
          <div className="space-y-5">
            <SubRail
              items={MONEY_PANELS}
              value={route.money}
              onChange={(panel) => go("money", panel)}
              label="Money sections"
            />
            {route.money === "pricing" && <MerchantPricingPanel merchantId={id} />}
            {route.money === "quote" && <MerchantQuotePreview id={id} />}
            {route.money === "credit" &&
              (ops ? (
                <MerchantCreditCard ops={ops} onSaved={refresh} />
              ) : (
                <SkeletonRows rows={3} label="Loading credit" />
              ))}
            {route.money === "invoices" && <InvoicesTab id={id} />}
            {route.money === "contracts" && <ContractsTab id={id} />}
            {route.money === "statement" && <StatementTab id={id} />}
            {route.money === "credits" && <CreditNotesTab id={id} />}
          </div>
        )}
        {route.tab === "connections" && (
          <div className="space-y-6">
            <MerchantIntegrationsTab id={id} />
          </div>
        )}
        {route.tab === "people" && (
          <div className="space-y-5">
            <SubRail
              items={PEOPLE_PANELS}
              value={route.people}
              onChange={(panel) => go("people", panel)}
              label="People and files sections"
            />
            {route.people === "team" && <MerchantTeamPanel merchant={m} />}
            {route.people === "contacts" && <MerchantContactsPanel id={id} />}
            {route.people === "locations" && <MerchantLocationsPanel id={id} />}
            {route.people === "documents" && <MerchantDocumentsPanel id={id} />}
            {route.people === "support" && <MerchantSupportPanel id={id} />}
            {route.people === "settings" && <SettingsTab m={m} onSaved={refresh} />}
            {route.people === "privacy" && <MerchantPrivacyCard id={id} />}
            {route.people === "activity" && (
              <div className="space-y-5">
                <SubRail
                  items={ACTIVITY_PANELS}
                  value={route.activity}
                  onChange={(panel) => go("people", panel)}
                  label="Activity sections"
                />
                {route.activity === "timeline" && <TimelineTab id={id} />}
                {route.activity === "activities" &&
                  (m.company_id ? (
                    <ActivityTimeline entityType="company" entityId={m.company_id} />
                  ) : (
                    <ReadActivities id={id} />
                  ))}
                {route.activity === "tasks" &&
                  (m.company_id ? (
                    <EntityTasks
                      entityType="company"
                      entityId={m.company_id}
                      companyId={m.company_id}
                    />
                  ) : (
                    <Panel>
                      <Empty
                        title="No tasks yet"
                        hint="Tasks appear once a CRM company is linked."
                      />
                    </Panel>
                  ))}
              </div>
            )}
          </div>
        )}
      </div>

      <Dialog
        open={confirm != null}
        onClose={() => setConfirm(null)}
        title={lc?.title ?? ""}
        description={lc?.body}
        footer={
          <>
            <QuietButton onClick={() => setConfirm(null)}>Cancel</QuietButton>
            <PrimaryAction
              disabled={busy}
              tone={lc?.danger ? "danger" : "accent"}
              onClick={() => confirm && void lifecycle(confirm)}
            >
              {busy ? "Working…" : lc?.cta}
            </PrimaryAction>
          </>
        }
      />
    </AdminPage>
  );
}

function DeliveryTimes({ ops }: { ops: MerchantOps }) {
  const h = ops.health;
  return (
    <dl className="grid grid-cols-2 gap-1 rounded-3xl border border-primary/10 bg-white p-1.5 sm:grid-cols-4">
      <Metric label="On time · 30 d" value={h.on_time_pct == null ? "—" : `${h.on_time_pct}%`} />
      <Metric
        label="Orders · 4 wk"
        value={String(h.trend.last_4w)}
        sub={
          h.trend.change_pct != null
            ? `${h.trend.change_pct > 0 ? "+" : ""}${h.trend.change_pct}% vs prior`
            : undefined
        }
      />
      <Metric
        label="Open exceptions"
        value={String(h.open_exceptions)}
        danger={h.open_exceptions > 0}
      />
      <Metric label="Open claims" value={String(h.open_claims)} danger={h.open_claims > 0} />
    </dl>
  );
}

function SubRail<T extends string>({
  items,
  value,
  onChange,
  label,
}: {
  items: { id: T; label: string }[];
  value: T;
  onChange: (id: T) => void;
  label: string;
}) {
  return (
    <div className="ops-tab-rail gap-1" role="tablist" aria-label={label}>
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={value === item.id}
          onClick={() => onChange(item.id)}
          className={cn(
            "min-h-10 shrink-0 rounded-full px-4 text-sm font-semibold whitespace-nowrap",
            value === item.id
              ? "bg-primary text-white"
              : "text-slate-600 hover:bg-white hover:text-primary"
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function Metric({
  label,
  value,
  sub,
  danger,
}: {
  label: string;
  value: string;
  sub?: string;
  danger?: boolean;
}) {
  return (
    <div className="min-w-0 rounded-2xl px-4 py-3">
      <dt className="text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase">
        {label}
      </dt>
      <dd
        className={cn(
          "mt-1 truncate text-2xl font-extrabold tracking-tight tabular-nums",
          danger ? "text-red-700" : "text-primary"
        )}
      >
        {value}
      </dd>
      {sub ? <dd className="text-xs text-slate-600">{sub}</dd> : null}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-slate-600">{label}</dt>
      <dd className={cn("truncate text-sm font-medium", value ? "text-primary" : "text-slate-500")}>
        {value || "—"}
      </dd>
    </div>
  );
}

function AtAGlance({
  m,
  onGoto,
}: {
  m: MerchantDetail;
  onGoto: (t: TabId, panel?: string) => void;
}) {
  const rows: [string, string, () => void][] = [
    ["Open orders", String(m.metrics.open_orders), () => onGoto("orders")],
    ["Team", String(m.counts.users ?? 0), () => onGoto("people", "team")],
    ["Contacts", String(m.counts.contacts ?? 0), () => onGoto("people", "contacts")],
    ["Locations", String(m.counts.locations ?? 0), () => onGoto("people", "locations")],
    ["API keys", String(m.counts.api_keys ?? 0), () => onGoto("connections")],
    ["Open tasks", String(m.counts.open_tasks ?? 0), () => onGoto("people", "tasks")],
    ["Contract", titleCase(m.contract_status) || "None", () => onGoto("money", "contracts")],
    ["Lifetime", money(m.metrics.lifetime_revenue_cents), () => onGoto("money", "statement")],
  ];
  return (
    <Panel title="At a glance">
      <ul className="-my-1 grid grid-cols-2 gap-1">
        {rows.map(([label, value, onClick]) => (
          <li key={label}>
            <button
              onClick={onClick}
              className="flex min-h-11 w-full flex-col items-start rounded-xl px-2 py-1.5 text-left hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-secondary"
            >
              <span className="text-xs text-slate-600">{label}</span>
              <span className="truncate text-base font-bold text-primary tabular-nums">
                {value}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function BusinessDetails({ m }: { m: MerchantDetail }) {
  const [all, setAll] = useState(false);
  const a = m.billing_address as Record<string, string>;
  const coverageVehicles = m.coverage?.assigned_vehicles?.length
    ? m.coverage.assigned_vehicles.map((v) => v.label).join(", ")
    : m.preferred_vehicles?.length
      ? m.preferred_vehicles.map(vehicleClassLabel).join(", ")
      : null;
  const zones = m.coverage?.delivery_zones?.length
    ? m.coverage.delivery_zones.map((z) => z.name || z.code).join(", ")
    : (m.delivery_zones ?? []).map(String).filter(Boolean).join(", ") || null;
  return (
    <Panel
      title="Business"
      aside={
        <button
          onClick={() => setAll((v) => !v)}
          aria-expanded={all}
          className="min-h-11 rounded-full px-3 text-sm font-semibold text-secondary hover:bg-secondary/5"
        >
          {all ? "Show less" : "Show all"}
        </button>
      }
    >
      <dl className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
        <Detail label="Email" value={m.email} />
        <Detail label="Phone" value={m.phone} />
        <Detail label="Payment terms" value={titleCase(m.payment_terms)} />
        <Detail
          label="Credit limit"
          value={m.credit_limit_cents != null ? money(m.credit_limit_cents) : "No limit"}
        />
        <Detail label="Service area" value={m.coverage?.service_area ?? m.service_area} />
        <Detail
          label="Billing city"
          value={[a?.city, a?.province].filter(Boolean).join(", ") || null}
        />
        {all && (
          <>
            <Detail label="Legal name" value={m.legal_name} />
            <Detail label="Industry" value={m.industry} />
            <Detail label="HST number" value={m.hst_number} />
            <Detail label="Business number" value={m.business_number} />
            <Detail label="Tax region" value={m.tax_region} />
            <Detail label="Tax exempt" value={m.tax_exempt ? "Yes" : "No"} />
            <Detail
              label="Tax & legal last edit"
              value={
                m.tax_legal_meta?.updated_at
                  ? `${m.tax_legal_meta.updated_by || "someone"} · ${dateTime(m.tax_legal_meta.updated_at)}`
                  : null
              }
            />
            <Detail
              label="Available credit"
              value={m.available_credit_cents != null ? money(m.available_credit_cents) : null}
            />
            <Detail label="Assigned vehicles" value={coverageVehicles} />
            <Detail label="Delivery zones" value={zones} />
            <Detail label="Activated" value={shortDate(m.activated_at)} />
            <Detail label="Created" value={shortDate(m.created_at)} />
          </>
        )}
      </dl>
    </Panel>
  );
}

function ReadActivities({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.activities(t, id), [id], {
    key: `merchant-activities-${id}`,
  });
  return (
    <Panel title="Activity">
      {!data ? (
        <SkeletonRows rows={3} label="Loading activity" />
      ) : data.length === 0 ? (
        <Empty title="No activity yet" hint="Calls, emails and notes show up here." />
      ) : (
        <ul className="-my-2 divide-y divide-primary/5">
          {data.map((a) => (
            <li key={a.id} className="py-3">
              <p className="text-sm font-medium text-primary">
                {a.subject ?? a.body ?? titleCase(a.activity_type)}
              </p>
              <p className="text-xs text-slate-600">
                {titleCase(a.activity_type)} · {relativeTime(a.occurred_at)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function TimelineTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.timeline(t, id), [id], {
    key: `merchant-timeline-${id}`,
  });
  return (
    <Panel title="Timeline">
      {!data ? (
        <SkeletonRows rows={4} label="Loading timeline" />
      ) : data.length === 0 ? (
        <Empty
          title="No events yet"
          hint="Orders, invoices and activity appear here as they happen."
        />
      ) : (
        <ol>
          {data.map((e, i) => (
            <li key={i} className="flex gap-3 pb-4 last:pb-0">
              <div className="flex flex-col items-center">
                <span
                  className={cn(
                    "mt-1.5 h-2 w-2 rounded-full",
                    e.kind === "invoice" ? "bg-amber-600" : "bg-primary"
                  )}
                />
                {i < data.length - 1 && <span className="w-px flex-1 bg-primary/10" />}
              </div>
              <div className="pb-1">
                <p className="text-sm font-medium text-primary">{e.title}</p>
                <p className="text-xs text-slate-600">
                  {titleCase(e.kind)} · {dateTime(e.at)}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}

function LazyAnalytics({ id }: { id: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [show, setShow] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || show) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setShow(true);
          io.disconnect();
        }
      },
      { rootMargin: "120px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [show]);
  return (
    <div ref={ref}>{show ? <AnalyticsTab id={id} /> : <div className="h-24" aria-hidden />}</div>
  );
}

function AnalyticsTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.analytics(t, id), [id], {
    key: `merchant-analytics-${id}`,
  });
  if (!data) return <SkeletonRows rows={3} label="Loading revenue" />;
  const months = data.revenue_by_month ?? [];
  const destinations = data.top_destinations ?? [];
  const maxRev = Math.max(1, ...months.map((r) => r.revenue_cents));
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
      <Panel title="Revenue by month">
        {months.length === 0 ? (
          <Empty title="No order history yet" />
        ) : (
          <div className="space-y-3">
            {months.map((r) => (
              <div key={r.month}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="text-primary">
                    {r.month} <span className="text-slate-600">· {r.orders} orders</span>
                  </span>
                  <span className="font-bold text-primary tabular-nums">
                    {money(r.revenue_cents)}
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${(r.revenue_cents / maxRev) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <Panel title="Top destinations">
        {destinations.length === 0 ? (
          <Empty title="No destinations yet" />
        ) : (
          <ul className="-my-2 divide-y divide-primary/5">
            {destinations.map((d) => (
              <li
                key={d.city}
                className="flex min-w-0 items-center justify-between gap-3 py-2.5 text-sm"
              >
                <span className="min-w-0 truncate text-primary">{d.city}</span>
                <span className="font-bold text-primary tabular-nums">{d.orders}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
