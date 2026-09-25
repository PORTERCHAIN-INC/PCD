"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Building2,
  CheckCircle2,
  Copy,
  ExternalLink,
  Globe,
  Info,
  KeyRound,
  ListChecks,
  Package,
  Receipt,
  Rocket,
  Settings as SettingsIcon,
  Tags,
  Users,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { getSystemLinks } from "@/lib/system-links";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchantStatusLabel } from "@/lib/catalog";
import {
  merchants,
  healthTone,
  merchantActionMessage,
  vehicleClassLabel,
  type MerchantDetail,
} from "@/lib/merchants";
import { EntityAlertsPanel } from "@/components/alerts/EntityAlertsPanel";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { EntityTasks } from "@/components/crm/EntityTasks";
import { Badge, Button, SectionCard, Spinner } from "@/components/crm/primitives";
import { money, shortDate, relativeTime, titleCase, dateTime } from "@/lib/crmFormat";
import AdminPage from "@/components/layout/AdminPage";

const MerchantContactsPanel = dynamic(
  () => import("@/components/merchants/MerchantContactsPanel"),
  { loading: () => <Spinner /> }
);
const MerchantLocationsPanel = dynamic(
  () => import("@/components/merchants/MerchantLocationsPanel"),
  { loading: () => <Spinner /> }
);
const MerchantPricingPanel = dynamic(() => import("@/components/merchants/MerchantPricingPanel"), {
  loading: () => <Spinner />,
});
const MerchantPrivacyCard = dynamic(() => import("@/components/merchants/MerchantPrivacyCard"), {
  loading: () => <Spinner />,
});
const MerchantStandingOrdersCard = dynamic(
  () => import("@/components/merchants/MerchantStandingOrdersCard"),
  { loading: () => <Spinner /> }
);
const MerchantTeamPanel = dynamic(() => import("@/components/merchants/MerchantTeamPanel"), {
  loading: () => <Spinner />,
});
const MerchantIntegrationsTab = dynamic(
  () => import("@/components/merchants/MerchantIntegrationsTab"),
  { loading: () => <Spinner /> }
);
const OrdersTab = dynamic(
  () => import("@/components/merchants/MerchantOrdersTab").then((m) => m.OrdersTab),
  { loading: () => <Spinner /> }
);
const StatementTab = dynamic(
  () => import("@/components/merchants/MerchantMoneyTabs").then((m) => m.StatementTab),
  { loading: () => <Spinner /> }
);
const InvoicesTab = dynamic(
  () => import("@/components/merchants/MerchantMoneyTabs").then((m) => m.InvoicesTab),
  { loading: () => <Spinner /> }
);
const CreditNotesTab = dynamic(
  () => import("@/components/merchants/MerchantMoneyTabs").then((m) => m.CreditNotesTab),
  { loading: () => <Spinner /> }
);
const ContractsTab = dynamic(
  () => import("@/components/merchants/MerchantMoneyTabs").then((m) => m.ContractsTab),
  { loading: () => <Spinner /> }
);
const SettingsTab = dynamic(
  () => import("@/components/merchants/MerchantSettingsTab").then((m) => m.SettingsTab),
  { loading: () => <Spinner /> }
);

const STATUS_TONE: Record<string, string> = {
  ACTIVE: "green",
  PENDING: "amber",
  ONBOARDING: "sky",
  SUSPENDED: "red",
  CLOSED: "slate",
};
const RISK_TONE: Record<string, string> = { low: "green", medium: "amber", high: "red" };
type TabId = "overview" | "orders" | "money" | "pricing" | "people" | "api" | "settings";
type PeoplePanel = "team" | "contacts" | "locations" | "activity";
type MoneyPanel = "invoices" | "contracts" | "statement" | "credits";
type ActivityPanel = "timeline" | "activities" | "tasks";

const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "overview", label: "Overview", icon: Info },
  { id: "orders", label: "Orders", icon: Package },
  { id: "money", label: "Billing", icon: Receipt },
  { id: "pricing", label: "Pricing", icon: Tags },
  { id: "people", label: "People", icon: Users },
  { id: "api", label: "Integrations", icon: KeyRound },
  { id: "settings", label: "Settings", icon: SettingsIcon },
];

const PEOPLE_PANELS: { id: PeoplePanel; label: string }[] = [
  { id: "team", label: "Team" },
  { id: "contacts", label: "Contacts" },
  { id: "locations", label: "Locations" },
  { id: "activity", label: "Activity" },
];

const MONEY_PANELS: { id: MoneyPanel; label: string }[] = [
  { id: "invoices", label: "Invoices" },
  { id: "contracts", label: "Contracts" },
  { id: "statement", label: "Statement" },
  { id: "credits", label: "Credit notes" },
];

const ACTIVITY_PANELS: { id: ActivityPanel; label: string }[] = [
  { id: "timeline", label: "Timeline" },
  { id: "activities", label: "CRM notes" },
  { id: "tasks", label: "Tasks" },
];

function parseMerchantTab(raw: string | null): {
  tab: TabId;
  people: PeoplePanel;
  money: MoneyPanel;
  activity: ActivityPanel;
} {
  if (raw === "invoices" || raw === "contracts" || raw === "statement" || raw === "credits") {
    return { tab: "money", people: "team", money: raw, activity: "timeline" };
  }
  if (raw === "team" || raw === "contacts" || raw === "locations") {
    return { tab: "people", people: raw, money: "invoices", activity: "timeline" };
  }
  if (raw === "activities" || raw === "tasks" || raw === "timeline") {
    return { tab: "people", people: "activity", money: "invoices", activity: raw };
  }
  if (raw === "analytics") {
    return { tab: "overview", people: "team", money: "invoices", activity: "timeline" };
  }
  if (TABS.some((t) => t.id === raw)) {
    return { tab: raw as TabId, people: "team", money: "invoices", activity: "timeline" };
  }
  return { tab: "overview", people: "team", money: "invoices", activity: "timeline" };
}

export default function MerchantDetailClient() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = params.id;
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const [tab, setTab] = useState<TabId>(() => parseMerchantTab(searchParams.get("tab")).tab);
  const [peoplePanel, setPeoplePanel] = useState<PeoplePanel>(
    () => parseMerchantTab(searchParams.get("tab")).people
  );
  const [moneyPanel, setMoneyPanel] = useState<MoneyPanel>(
    () => parseMerchantTab(searchParams.get("tab")).money
  );
  const [activityPanel, setActivityPanel] = useState<ActivityPanel>(
    () => parseMerchantTab(searchParams.get("tab")).activity
  );
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [copied, setCopied] = useState<"id" | "portal" | null>(null);
  const merchantPortalBase =
    getSystemLinks().find((l) => l.id === "merchant")?.href ?? "http://localhost:3001";

  const { data: m, error } = useApiData((t) => merchants.detail(t, id), [id, version], {
    key: `merchant-detail-${id}`,
  });
  const refresh = () => setVersion((v) => v + 1);

  async function copyText(kind: "id" | "portal", value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(kind);
      window.setTimeout(() => setCopied(null), 1500);
    } catch {
      setActionError("Could not copy to clipboard");
    }
  }

  function gotoTab(
    tid: TabId,
    extras?: { people?: PeoplePanel; money?: MoneyPanel; activity?: ActivityPanel }
  ) {
    setTab(tid);
    if (extras?.people) setPeoplePanel(extras.people);
    if (extras?.money) setMoneyPanel(extras.money);
    if (extras?.activity) setActivityPanel(extras.activity);
    const qs = new URLSearchParams();
    qs.set("tab", tid);
    if (tid === "people") {
      qs.set("panel", extras?.activity ?? extras?.people ?? peoplePanel);
    }
    if (tid === "money") qs.set("panel", extras?.money ?? moneyPanel);
    router.replace(`/merchants/${id}?${qs.toString()}`, { scroll: false });
  }

  useEffect(() => {
    const parsed = parseMerchantTab(searchParams.get("tab"));
    const panel = searchParams.get("panel");
    setTab(parsed.tab);
    if (parsed.tab === "people") {
      if (panel === "team" || panel === "contacts" || panel === "locations") {
        setPeoplePanel(panel);
      } else if (
        panel === "activity" ||
        panel === "timeline" ||
        panel === "activities" ||
        panel === "tasks"
      ) {
        setPeoplePanel("activity");
        if (panel === "timeline" || panel === "activities" || panel === "tasks") {
          setActivityPanel(panel);
        }
      } else {
        setPeoplePanel(parsed.people);
        if (parsed.activity) setActivityPanel(parsed.activity);
      }
    }
    if (parsed.tab === "money") {
      if (panel === "invoices" || panel === "contracts" || panel === "statement")
        setMoneyPanel(panel);
      else setMoneyPanel(parsed.money);
    }
  }, [searchParams]);

  async function lifecycle(action: "approve" | "suspend" | "unsuspend" | "reopen") {
    setBusy(true);
    setActionError(null);
    try {
      const token = await getApiToken();
      if (action === "approve") await merchants.approve(token, id);
      else if (action === "suspend") await merchants.suspend(token, id);
      else if (action === "unsuspend") await merchants.unsuspend(token, id);
      else await merchants.reopen(token, id);
      refresh();
    } catch (e) {
      setActionError(merchantActionMessage(e, `${action} failed`));
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!m) return <Spinner label="Loading merchant…" />;

  return (
    <AdminPage>
      <button
        onClick={() => router.push("/merchants")}
        className="flex min-h-10 items-center gap-1.5 text-sm text-muted hover:text-primary"
      >
        <ArrowLeft className="h-4 w-4" /> All merchants
      </button>

      {/* Header */}
      <div className="min-w-0 rounded-2xl border border-primary/10 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex min-w-0 items-start gap-3 sm:items-center sm:gap-4">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-secondary/10 text-secondary sm:h-14 sm:w-14">
              {m.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={m.logo_url} alt="" className="h-full w-full object-cover" />
              ) : (
                <Building2 className="h-7 w-7" />
              )}
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-lg font-bold text-primary sm:text-xl">
                  {m.company_name}
                </h1>
                <Badge tone={STATUS_TONE[m.status] ?? "slate"}>
                  {m.status_label || merchantStatusLabel(m.status)}
                </Badge>
                {m.owner_clerk_linked ? (
                  <Badge tone="sky">Clerk</Badge>
                ) : (
                  <Badge tone="amber">Clerk off</Badge>
                )}
                {m.api_connected ? (
                  <Badge tone="green">API</Badge>
                ) : (
                  <Badge tone="slate">API off</Badge>
                )}
                {m.cod_enabled ? <Badge tone="green">COD</Badge> : null}
              </div>
              <p className="mt-0.5 break-words text-sm text-muted">
                {m.industry ?? "—"}
                {m.city ? ` · ${[m.city, m.province].filter(Boolean).join(", ")}` : ""}
                {m.website ? (
                  <>
                    {" · "}
                    <a
                      href={m.website}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-secondary"
                    >
                      <Globe className="h-3 w-3" /> Website
                    </a>
                  </>
                ) : null}
              </p>
            </div>
          </div>
          <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap sm:items-center">
            <button
              type="button"
              onClick={() => void copyText("id", m.id)}
              className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
              title={m.id}
            >
              <Copy className="h-4 w-4" />
              {copied === "id" ? "Copied id" : "Copy id"}
            </button>
            <a
              href={merchantPortalBase}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
            >
              <ExternalLink className="h-4 w-4" /> Portal
            </a>
            <button
              type="button"
              onClick={() => void copyText("portal", merchantPortalBase)}
              className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
            >
              <Copy className="h-4 w-4" />
              {copied === "portal" ? "Copied URL" : "Copy portal"}
            </button>
            <a
              href={`${merchantPortalBase}/billing?tab=cod`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
            >
              <ExternalLink className="h-4 w-4" /> COD / Connect
            </a>
            <Link
              href={`/booking-drafts?merchant_id=${m.id}`}
              className="inline-flex min-h-10 items-center justify-center rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
            >
              Drafts
            </Link>
            <Link
              href={`/support?merchant_id=${m.id}`}
              className="inline-flex min-h-10 items-center justify-center rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
            >
              Support
            </Link>
            <Link
              href={`/claims?merchant_id=${m.id}`}
              className="inline-flex min-h-10 items-center justify-center rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
            >
              Claims
            </Link>
            <Link
              href="/settings?section=users&tab=merchant"
              className="col-span-2 inline-flex min-h-10 items-center justify-center rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg sm:col-span-1"
            >
              Users directory
            </Link>
            {(m.status === "PENDING" || m.status === "ONBOARDING") && (
              <Button onClick={() => lifecycle("approve")} disabled={busy}>
                <Rocket className="h-4 w-4" /> Approve
              </Button>
            )}
            {m.status === "ACTIVE" && (
              <Button variant="outline" onClick={() => lifecycle("suspend")} disabled={busy}>
                Suspend
              </Button>
            )}
            {m.status === "SUSPENDED" && (
              <Button onClick={() => lifecycle("unsuspend")} disabled={busy}>
                Unsuspend
              </Button>
            )}
            {m.status === "CLOSED" && (
              <Button variant="outline" onClick={() => lifecycle("reopen")} disabled={busy}>
                Reopen
              </Button>
            )}
          </div>
        </div>
        {actionError && (
          <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {actionError}
          </p>
        )}

        {/* Metric tiles + health + AI */}
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <HealthCard score={m.health} />
          <Metric
            label="Monthly revenue"
            value={money(m.metrics.monthly_revenue_cents)}
            sub={`${m.metrics.monthly_orders} orders / 30d`}
          />
          <Metric
            label="AR outstanding"
            value={money(m.metrics.outstanding_balance_cents)}
            sub={
              m.metrics.overdue_balance_cents > 0
                ? `${money(m.metrics.overdue_balance_cents)} overdue`
                : (m.metrics.crm_outstanding_balance_cents ?? 0) > 0
                  ? `CRM sales ${money(m.metrics.crm_outstanding_balance_cents ?? 0)} tracked separately`
                  : "Invoiced + not yet invoiced − credits"
            }
            danger={m.metrics.overdue_balance_cents > 0}
          />
          <Metric
            label="Lifetime"
            value={money(m.metrics.lifetime_revenue_cents)}
            sub={`${m.metrics.lifetime_orders} orders`}
          />
        </div>

        <AiPanel ai={m.ai} />
      </div>

      {/* Tabs */}
      <div className="sticky top-0 z-10 min-w-0 rounded-2xl border border-primary/10 bg-white/95 shadow-sm backdrop-blur">
        <div className="ops-tab-rail" role="tablist" aria-label="Merchant sections">
          {TABS.map(({ id: tid, label, icon: Icon }) => (
            <button
              key={tid}
              type="button"
              role="tab"
              aria-selected={tab === tid}
              onClick={() => gotoTab(tid)}
              className={cn(
                "flex min-h-10 shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors",
                tab === tid ? "bg-secondary text-white" : "text-primary/70 hover:bg-gray-bg"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="min-w-0">
        {tab === "overview" && <OverviewTab m={m} onGoto={gotoTab} />}
        {tab === "orders" && <OrdersTab id={id} />}
        {tab === "money" && (
          <div className="space-y-4">
            <SubRail
              items={MONEY_PANELS}
              value={moneyPanel}
              onChange={(panel) => gotoTab("money", { money: panel })}
              label="Billing sections"
            />
            {moneyPanel === "invoices" && <InvoicesTab id={id} />}
            {moneyPanel === "contracts" && <ContractsTab id={id} />}
            {moneyPanel === "statement" && <StatementTab id={id} />}
            {moneyPanel === "credits" && <CreditNotesTab id={id} />}
          </div>
        )}
        {tab === "pricing" && <MerchantPricingPanel merchantId={id} />}
        {tab === "people" && (
          <div className="space-y-4">
            <SubRail
              items={PEOPLE_PANELS}
              value={peoplePanel}
              onChange={(panel) => gotoTab("people", { people: panel })}
              label="People sections"
            />
            {peoplePanel === "team" && <MerchantTeamPanel merchant={m} />}
            {peoplePanel === "contacts" && <MerchantContactsPanel id={id} />}
            {peoplePanel === "locations" && <MerchantLocationsPanel id={id} />}
            {peoplePanel === "activity" && (
              <div className="space-y-4">
                <SubRail
                  items={ACTIVITY_PANELS}
                  value={activityPanel}
                  onChange={(panel) => {
                    setActivityPanel(panel);
                    router.replace(`/merchants/${id}?tab=people&panel=${panel}`, { scroll: false });
                  }}
                  label="Activity sections"
                />
                {activityPanel === "timeline" && <TimelineTab id={id} />}
                {activityPanel === "activities" &&
                  (m.company_id ? (
                    <ActivityTimeline entityType="company" entityId={m.company_id} />
                  ) : (
                    <ReadActivities id={id} />
                  ))}
                {activityPanel === "tasks" &&
                  (m.company_id ? (
                    <EntityTasks
                      entityType="company"
                      entityId={m.company_id}
                      companyId={m.company_id}
                    />
                  ) : (
                    <p className="py-10 text-center text-sm text-muted">
                      Tasks available once a CRM company is linked.
                    </p>
                  ))}
              </div>
            )}
          </div>
        )}
        {tab === "api" && <MerchantIntegrationsTab id={id} />}
        {tab === "settings" && <SettingsTab m={m} onSaved={refresh} />}
      </div>
    </AdminPage>
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
    <div
      className="ops-tab-rail rounded-xl border border-primary/10 bg-white"
      role="tablist"
      aria-label={label}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={value === item.id}
          onClick={() => onChange(item.id)}
          className={cn(
            "min-h-10 shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium whitespace-nowrap",
            value === item.id ? "bg-primary text-white" : "text-muted hover:bg-gray-bg"
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
    <div className="min-w-0 rounded-xl border border-primary/10 p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 truncate text-xl font-bold tabular-nums text-primary">{value}</p>
      {sub && <p className={cn("text-xs", danger ? "text-red-600" : "text-muted")}>{sub}</p>}
    </div>
  );
}

function HealthCard({ score }: { score: number }) {
  const color = score >= 70 ? "#16a34a" : score >= 40 ? "#f59e0b" : "#dc2626";
  return (
    <div className="flex min-w-0 items-center gap-4 rounded-xl border border-primary/10 p-4">
      <div
        className="relative flex h-16 w-16 items-center justify-center rounded-full"
        style={{ background: `conic-gradient(${color} ${score * 3.6}deg, #e2e8f0 0deg)` }}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-sm font-bold text-primary">
          {score}
        </div>
      </div>
      <div>
        <p className="text-xs text-muted">Health score</p>
        <p className="text-lg font-bold text-primary">
          {score >= 70 ? "Healthy" : score >= 40 ? "Watch" : "At risk"}
        </p>
      </div>
    </div>
  );
}

function AiPanel({ ai }: { ai: MerchantDetail["ai"] }) {
  const modelAssisted = ai.actions_source === "nvidia_nim";
  return (
    <div className="mt-4 rounded-xl border border-primary/15 bg-white p-4">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
        <ListChecks className="h-4 w-4 text-secondary" /> Next actions
      </div>
      <p className="mb-2 text-xs text-muted">
        {modelAssisted
          ? "Risk scores stay rule-based · action copy NVIDIA NIM · read-only"
          : "From orders, AR, and contract dates — not a model."}
      </p>
      <div className="flex flex-wrap gap-2">
        <Badge tone={RISK_TONE[ai.risk_score]}>Risk: {titleCase(ai.risk_score)}</Badge>
        <Badge tone={RISK_TONE[ai.payment_risk]}>Payment: {titleCase(ai.payment_risk)}</Badge>
        <Badge tone={RISK_TONE[ai.renewal_risk]}>Renewal: {titleCase(ai.renewal_risk)}</Badge>
        <Badge tone="sky">Trend: {titleCase(ai.revenue_trend)}</Badge>
        {modelAssisted ? <Badge tone="sky">NVIDIA NIM</Badge> : null}
      </div>
      <ul className="mt-3 space-y-1">
        {ai.suggested_actions.map((s, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-primary">
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-secondary" />
            {s}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-sm text-primary">{value || "—"}</dd>
    </div>
  );
}

function OverviewTab({
  m,
  onGoto,
}: {
  m: MerchantDetail;
  onGoto: (
    t: TabId,
    extras?: { people?: PeoplePanel; money?: MoneyPanel; activity?: ActivityPanel }
  ) => void;
}) {
  const a = m.billing_address as Record<string, string>;
  return (
    <div className="space-y-5">
      {m.portal_ready === false && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          This company is not portal-ready. Open{" "}
          <button
            type="button"
            className="font-semibold underline"
            onClick={() => onGoto("people", { people: "team" })}
          >
            People → Team
          </button>{" "}
          to invite the owner and activate the seat.
        </div>
      )}
      <MerchantStandingOrdersCard id={m.id} compact />
      <MerchantPrivacyCard id={m.id} compact />
      <div className="grid gap-5 lg:grid-cols-3">
        <SectionCard title="Business details" className="lg:col-span-2">
          <dl className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2 sm:p-5 md:grid-cols-3">
            <Detail label="Legal name" value={m.legal_name} />
            <Detail label="Industry" value={m.industry} />
            <Detail label="Email" value={m.email} />
            <Detail label="Phone" value={m.phone} />
            <Detail label="HST number" value={m.hst_number} />
            <Detail label="Business number" value={m.business_number} />
            <Detail label="Tax region" value={m.tax_region} />
            <Detail label="Tax exempt" value={m.tax_exempt ? "Yes" : "No"} />
            <Detail
              label="Tax & legal last writer"
              value={
                m.tax_legal_meta?.updated_at
                  ? `${m.tax_legal_meta.updated_by || "someone"} · ${dateTime(m.tax_legal_meta.updated_at)}`
                  : null
              }
            />
            <Detail label="Payment terms" value={titleCase(m.payment_terms)} />
            <Detail
              label="Credit limit"
              value={m.credit_limit_cents != null ? money(m.credit_limit_cents) : null}
            />
            <Detail
              label="Available credit"
              value={m.available_credit_cents != null ? money(m.available_credit_cents) : null}
            />
            <Detail label="Service area" value={m.coverage?.service_area ?? m.service_area} />
            <Detail
              label="Assigned vehicles"
              value={
                m.coverage?.assigned_vehicles?.length
                  ? m.coverage.assigned_vehicles.map((v) => v.label).join(", ")
                  : m.preferred_vehicles?.length
                    ? m.preferred_vehicles.map(vehicleClassLabel).join(", ")
                    : null
              }
            />
            <Detail
              label="Delivery zones"
              value={
                m.coverage?.delivery_zones?.length
                  ? m.coverage.delivery_zones.map((z) => z.name || z.code).join(", ")
                  : (m.delivery_zones ?? []).map(String).filter(Boolean).join(", ") || null
              }
            />
            <Detail
              label="Billing city"
              value={[a?.city, a?.province].filter(Boolean).join(", ") || null}
            />
            <Detail label="Activated" value={shortDate(m.activated_at)} />
            <Detail label="Created" value={shortDate(m.created_at)} />
          </dl>
        </SectionCard>
        <SectionCard title="At a glance">
          <div className="space-y-3 p-5 text-sm">
            <QuickRow
              label="Open orders"
              value={String(m.metrics.open_orders)}
              onClick={() => onGoto("orders")}
            />
            <QuickRow
              label="Contacts"
              value={String(m.counts.contacts ?? 0)}
              onClick={() => onGoto("people", { people: "contacts" })}
            />
            <QuickRow
              label="Locations"
              value={String(m.counts.locations ?? 0)}
              onClick={() => onGoto("people", { people: "locations" })}
            />
            <QuickRow
              label="Team members"
              value={String(m.counts.users ?? 0)}
              onClick={() => onGoto("people", { people: "team" })}
            />
            <QuickRow
              label="API keys"
              value={String(m.counts.api_keys ?? 0)}
              onClick={() => onGoto("api")}
            />
            <QuickRow
              label="Open tasks"
              value={String(m.counts.open_tasks ?? 0)}
              onClick={() => onGoto("people", { people: "activity", activity: "tasks" })}
            />
            <QuickRow
              label="Contract"
              value={titleCase(m.contract_status)}
              onClick={() => onGoto("money", { money: "contracts" })}
            />
            <QuickRow
              label="Credit notes"
              value="View"
              onClick={() => onGoto("money", { money: "credits" })}
            />
            <Link
              href={`/booking-drafts?merchant_id=${m.id}`}
              className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-sm hover:bg-gray-bg"
            >
              <span className="text-muted">Booking drafts</span>
              <span className="font-semibold text-secondary">Open →</span>
            </Link>
          </div>
        </SectionCard>
      </div>
      <EntityAlertsPanel
        recipientType="merchant"
        recipientId={m.id}
        careHref={`/support?merchant_id=${m.id}`}
      />
      <LazyAnalytics id={m.id} />
    </div>
  );
}

function QuickRow({
  label,
  value,
  onClick,
}: {
  label: string;
  value: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left hover:bg-gray-bg"
    >
      <span className="text-muted">{label}</span>
      <span className="font-semibold text-primary">{value}</span>
    </button>
  );
}

function ReadActivities({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.activities(t, id), [id], {
    key: `merchant-activities-${id}`,
  });
  return (
    <SectionCard title="Activity">
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((a) => (
          <div key={a.id} className="px-5 py-3">
            <p className="text-sm text-primary">
              {a.subject ?? a.body ?? titleCase(a.activity_type)}
            </p>
            <p className="text-xs text-muted">
              {titleCase(a.activity_type)} · {relativeTime(a.occurred_at)}
            </p>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">No activity yet.</p>
        )}
      </div>
    </SectionCard>
  );
}

function TimelineTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.timeline(t, id), [id], {
    key: `merchant-timeline-${id}`,
  });
  const tone: Record<string, string> = {
    activity: "bg-secondary",
    order: "bg-violet-500",
    invoice: "bg-amber-500",
  };
  return (
    <SectionCard title="Timeline">
      <div className="space-y-0 p-5">
        {(data ?? []).map((e, i) => (
          <div key={i} className="flex gap-3 pb-4 last:pb-0">
            <div className="flex flex-col items-center">
              <span className={cn("h-2.5 w-2.5 rounded-full", tone[e.kind] ?? "bg-slate-400")} />
              {i < (data?.length ?? 0) - 1 && <span className="w-px flex-1 bg-primary/10" />}
            </div>
            <div className="-mt-1 pb-1">
              <p className="text-sm text-primary">{e.title}</p>
              <p className="text-xs text-muted">
                {titleCase(e.kind)} · {dateTime(e.at)}
              </p>
            </div>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="py-10 text-center text-sm text-muted">No timeline events.</p>
        )}
      </div>
    </SectionCard>
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
    <div ref={ref}>{show ? <AnalyticsTab id={id} /> : <div className="h-48" aria-hidden />}</div>
  );
}

function AnalyticsTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.analytics(t, id), [id], {
    key: `merchant-analytics-${id}`,
  });
  if (!data) return <Spinner />;
  const months = data.revenue_by_month ?? [];
  const destinations = data.top_destinations ?? [];
  const maxRev = Math.max(1, ...months.map((r) => r.revenue_cents));
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <SectionCard title="Revenue by month" className="lg:col-span-2">
        <div className="space-y-3 p-5">
          {months.map((r) => (
            <div key={r.month}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="text-primary">
                  {r.month} <span className="text-muted">· {r.orders} orders</span>
                </span>
                <span className="font-semibold text-primary">{money(r.revenue_cents)}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-gray-bg">
                <div
                  className="h-full rounded-full bg-secondary"
                  style={{ width: `${(r.revenue_cents / maxRev) * 100}%` }}
                />
              </div>
            </div>
          ))}
          {months.length === 0 && (
            <p className="py-6 text-center text-sm text-muted">No order history yet.</p>
          )}
        </div>
      </SectionCard>
      <SectionCard title="Top destinations">
        <div className="divide-y divide-primary/5">
          {destinations.map((d) => (
            <div
              key={d.city}
              className="flex min-w-0 items-center justify-between gap-3 px-5 py-3 text-sm"
            >
              <span className="min-w-0 truncate text-primary">{d.city}</span>
              <span className="font-semibold text-primary">{d.orders}</span>
            </div>
          ))}
          {destinations.length === 0 && (
            <p className="px-5 py-8 text-center text-sm text-muted">No destinations yet.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
