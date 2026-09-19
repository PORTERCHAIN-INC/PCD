"use client";

import { useEffect, useState } from "react";
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
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import { publicEnv } from "@/lib/env";
import { getSystemLinks } from "@/lib/system-links";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchantStatusLabel } from "@/lib/catalog";
import {
  merchants,
  healthTone,
  merchantActionMessage,
  BILLING_CYCLES,
  RETAIL_VEHICLE_OPTIONS,
  vehicleClassLabel,
  type MerchantDetail,
} from "@/lib/merchants";
import { financeApi } from "@/lib/finance";
import { withStaffStepUp } from "@/lib/staff-step-up";
import MerchantBillingContactsCard from "@/components/merchants/MerchantBillingContactsCard";
import MerchantContactsPanel from "@/components/merchants/MerchantContactsPanel";
import MerchantLocationsPanel from "@/components/merchants/MerchantLocationsPanel";
import MerchantPricingPanel from "@/components/merchants/MerchantPricingPanel";
import MerchantPrivacyCard from "@/components/merchants/MerchantPrivacyCard";
import MerchantStandingOrdersCard from "@/components/merchants/MerchantStandingOrdersCard";
import MerchantTeamPanel from "@/components/merchants/MerchantTeamPanel";
import { EntityAlertsPanel } from "@/components/alerts/EntityAlertsPanel";
import { ListPager } from "@/components/crm/ListPager";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { EntityTasks } from "@/components/crm/EntityTasks";
import {
  Badge,
  Button,
  Field,
  Input,
  Select,
  SectionCard,
  Spinner,
} from "@/components/crm/primitives";
import { money, shortDate, relativeTime, titleCase, dateTime } from "@/lib/crmFormat";

const STATUS_TONE: Record<string, string> = {
  ACTIVE: "green",
  PENDING: "amber",
  ONBOARDING: "sky",
  SUSPENDED: "red",
  CLOSED: "slate",
};
const RISK_TONE: Record<string, string> = { low: "green", medium: "amber", high: "red" };
const TERMS = ["IMMEDIATE", "NET_7", "NET_14", "NET_15", "NET_30", "NET_45", "CUSTOM"];
const SUPPORT_TIERS = ["standard", "priority", "enterprise"] as const;
const CA_TAX_REGIONS = [
  "AB",
  "BC",
  "MB",
  "NB",
  "NL",
  "NS",
  "NT",
  "NU",
  "ON",
  "PE",
  "QC",
  "SK",
  "YT",
] as const;

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
  { id: "api", label: "API", icon: KeyRound },
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

const CONTRACT_STATUSES = ["draft", "active", "expired", "cancelled"] as const;

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

export default function MerchantDetailPage() {
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
    <div className="min-w-0 space-y-5">
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
        {tab === "api" && <ApiTab id={id} />}
        {tab === "settings" && <SettingsTab m={m} onSaved={refresh} />}
      </div>
    </div>
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
      <AnalyticsTab id={m.id} />
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

const ORDER_FILTER_STATES = [
  "DISPATCH_READY",
  "DRIVER_ASSIGNED",
  "IN_TRANSIT",
  "DELIVERED",
  "POD_COMPLETED",
  "CANCELLED",
  "FAILED",
] as const;

function OrdersTab({ id }: { id: string }) {
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState<string>("");
  const [q, setQ] = useState("");
  const { data } = useApiData(
    (t) =>
      merchants.orders(t, id, {
        limit: 50,
        offset,
        state: state || undefined,
      }),
    [id, offset, state],
    {
      key: `merchant-orders-${id}-${offset}-${state || "all"}`,
    }
  );
  const items = data?.items ?? [];
  const needle = q.trim().toLowerCase();
  const visible = needle
    ? items.filter((o) => {
        const hay =
          `${o.order_number ?? ""} ${o.tracking_number ?? ""} ${o.state ?? ""}`.toLowerCase();
        return hay.includes(needle);
      })
    : items;
  const grouped = new Map<string, typeof visible>();
  const loose: typeof visible = [];
  for (const order of visible) {
    const jobId = order.route_import_job_id;
    if (jobId) {
      const rows = grouped.get(jobId) ?? [];
      rows.push(order);
      grouped.set(jobId, rows);
    } else {
      loose.push(order);
    }
  }
  return (
    <div className="space-y-5">
      <MerchantStandingOrdersCard id={id} />
      <SectionCard title={`Orders (${data?.total ?? 0})`}>
        <div className="space-y-3 border-b border-primary/5 px-4 py-3 sm:px-5">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                setState("");
                setOffset(0);
              }}
              className={cn(
                "rounded-lg px-2.5 py-1 text-xs font-medium",
                !state ? "bg-secondary text-white" : "bg-gray-bg text-muted hover:text-primary"
              )}
            >
              All
            </button>
            {ORDER_FILTER_STATES.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => {
                  setState(s);
                  setOffset(0);
                }}
                className={cn(
                  "rounded-lg px-2.5 py-1 text-xs font-medium",
                  state === s
                    ? "bg-secondary text-white"
                    : "bg-gray-bg text-muted hover:text-primary"
                )}
              >
                {titleCase(s)}
              </button>
            ))}
          </div>
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter this page by order / tracking…"
            className="max-w-sm"
          />
        </div>
        <div className="ops-table-scroll">
          <table className="w-full min-w-[36rem] text-left text-sm">
            <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-2">Order</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Amount</th>
                <th className="px-4 py-2">Scheduled</th>
                <th className="px-4 py-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {[...grouped.entries()].map(([jobId, rows]) => (
                <OrdersGroupRows key={jobId} label={`Route job ${jobId.slice(0, 8)}`} rows={rows} />
              ))}
              {loose.length > 0 && grouped.size > 0 ? (
                <OrdersGroupRows label="Other orders" rows={loose} />
              ) : null}
              {grouped.size === 0 ? visible.map((o) => <OrderRow key={o.id} order={o} />) : null}
            </tbody>
          </table>
          {visible.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-muted">No orders match.</p>
          )}
        </div>
        <div className="px-4 pb-3">
          <ListPager
            total={data?.total ?? 0}
            limit={data?.limit ?? 50}
            offset={offset}
            onPage={setOffset}
          />
        </div>
      </SectionCard>
    </div>
  );
}

function OrdersGroupRows({
  label,
  rows,
}: {
  label: string;
  rows: Array<{
    id: string;
    order_number: string;
    state: string;
    amount_cents: number;
    scheduled_at: string | null;
    created_at: string | null;
  }>;
}) {
  return (
    <>
      <tr className="bg-gray-bg/60">
        <td
          colSpan={5}
          className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-muted"
        >
          {label}
        </td>
      </tr>
      {rows.map((order) => (
        <OrderRow key={order.id} order={order} />
      ))}
    </>
  );
}

function OrderRow({
  order,
}: {
  order: {
    id: string;
    order_number: string;
    state: string;
    amount_cents: number;
    scheduled_at: string | null;
    created_at: string | null;
  };
}) {
  return (
    <tr className="border-b border-primary/5">
      <td className="px-4 py-2 font-medium text-primary">
        <Link href={`/orders/${order.id}`} className="text-secondary hover:underline">
          {order.order_number}
        </Link>
      </td>
      <td className="px-4 py-2">
        <Badge tone="sky">{titleCase(order.state)}</Badge>
      </td>
      <td className="px-4 py-2">{money(order.amount_cents)}</td>
      <td className="px-4 py-2">{shortDate(order.scheduled_at)}</td>
      <td className="px-4 py-2">{shortDate(order.created_at)}</td>
    </tr>
  );
}

function StatementTab({ id }: { id: string }) {
  const { data, error } = useApiData((t) => merchants.statement(t, id), [id], {
    key: `merchant-statement-${id}`,
  });
  if (error) {
    return (
      <SectionCard title="Current billing period">
        <p className="px-5 py-4 text-sm text-red-600">{error}</p>
      </SectionCard>
    );
  }
  if (!data) {
    return (
      <SectionCard title="Current billing period">
        <div className="px-5 py-8">
          <Spinner label="Loading statement…" />
        </div>
      </SectionCard>
    );
  }
  return (
    <SectionCard title="Current billing period">
      <div className="space-y-3 px-5 py-4 text-sm">
        <p className="text-xs text-muted">
          {shortDate(data.period_start)} → {shortDate(data.period_end)} ·{" "}
          {titleCase(data.billing_cycle)} · {titleCase(data.payment_terms)} ({data.net_terms_days}{" "}
          days)
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Metric label="Outstanding" value={money(data.outstanding_balance_cents)} />
          <Metric label="Invoiced AR" value={money(data.outstanding_invoices_cents)} />
          <Metric label="Uninvoiced" value={money(data.uninvoiced_orders_cents)} />
          <Metric label="Credit notes" value={money(data.credit_notes_cents)} />
          <Metric label="Period orders" value={String(data.monthly_orders)} />
          <Metric label="Period spend" value={money(data.monthly_spend_cents)} />
        </div>
        <p className="text-xs text-muted">
          Stripe checkout {data.stripe_enabled ? "enabled" : "off"} for this company. Detailed line
          CSV stays on the merchant portal Billing → Statement export.
        </p>
      </div>
    </SectionCard>
  );
}

function InvoicesTab({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => merchants.invoices(t, id), [id], {
    key: `merchant-invoices-${id}`,
  });
  const [busy, setBusy] = useState<"preview" | "generate" | null>(null);
  const [remindingId, setRemindingId] = useState<string | null>(null);
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof merchants.arPreview>> | null>(
    null
  );
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const outstanding = (data ?? [])
    .filter((i) => i.status !== "paid" && i.status !== "void")
    .reduce((s, i) => s + i.total_cents, 0);

  async function runPreview() {
    setBusy("preview");
    setError(null);
    try {
      const token = await getApiToken();
      setPreview(await merchants.arPreview(token, id));
      setMessage(null);
    } catch (e) {
      setError(merchantActionMessage(e, "Could not preview invoices"));
    } finally {
      setBusy(null);
    }
  }

  async function runGenerate() {
    if (
      !window.confirm(
        "Create invoices for delivered / POD orders in the last closed billing cycle?"
      )
    ) {
      return;
    }
    setBusy("generate");
    setError(null);
    try {
      const token = await getApiToken();
      const result = await merchants.arGenerate(token, id);
      setMessage(
        `Created ${result.created_count} invoice(s); skipped ${result.skipped_count} already billed.`
      );
      setPreview(null);
      void refetch();
    } catch (e) {
      setError(merchantActionMessage(e, "Could not generate invoices"));
    } finally {
      setBusy(null);
    }
  }

  async function runRemind(invoiceId: string) {
    setRemindingId(invoiceId);
    setError(null);
    try {
      const token = await getApiToken();
      const result = await withStaffStepUp(token, () => financeApi.remindInvoice(token, invoiceId));
      setMessage(`Reminder sent to ${result.email} for ${result.invoice_number}.`);
      void refetch();
    } catch (e) {
      setError(merchantActionMessage(e, "Could not send reminder"));
    } finally {
      setRemindingId(null);
    }
  }

  return (
    <SectionCard
      title="Delivery invoices (ops AR)"
      action={
        <span className="text-sm text-muted">
          Outstanding <span className="font-bold text-primary">{money(outstanding)}</span>
        </span>
      }
    >
      <div className="space-y-3 border-b border-primary/5 px-4 py-3 sm:px-5">
        <p className="text-xs text-muted">
          Generate covers delivered and POD orders in the last closed cycle for this company. Leave
          Finance for cross-merchant runs and recording payments.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" disabled={busy !== null} onClick={() => void runPreview()}>
            {busy === "preview" ? "Previewing…" : "Preview cycle"}
          </Button>
          <Button disabled={busy !== null} onClick={() => void runGenerate()}>
            {busy === "generate" ? "Generating…" : "Generate invoices"}
          </Button>
        </div>
        {preview && (
          <p className="text-sm text-primary">
            {preview.order_count} order(s) · {money(preview.uninvoiced_cents)} uninvoiced ·{" "}
            {titleCase(preview.payment_terms || "terms")} · {preview.billing_cycle || "cycle"}
          </p>
        )}
        {message && <p className="text-sm text-secondary">{message}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((inv) => {
          const remindable =
            inv.status === "overdue" || inv.status === "sent" || inv.status === "pending";
          return (
            <div
              key={inv.id}
              className="flex min-w-0 flex-wrap items-center justify-between gap-2 px-4 py-3 sm:px-5"
            >
              <div>
                <p className="text-sm font-medium text-primary">
                  <Link
                    href={`/finance/invoices/${inv.id}`}
                    className="text-secondary hover:underline"
                  >
                    {inv.invoice_number}
                  </Link>
                </p>
                <p className="text-xs text-muted">
                  {money(inv.total_cents)} · {titleCase(inv.net_terms)} · due{" "}
                  {shortDate(inv.due_date)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {remindable ? (
                  <Button
                    variant="outline"
                    disabled={remindingId !== null || busy !== null}
                    onClick={() => void runRemind(inv.id)}
                  >
                    {remindingId === inv.id ? "Sending…" : "Remind"}
                  </Button>
                ) : null}
                <Badge
                  tone={
                    inv.status === "paid" ? "green" : inv.status === "overdue" ? "red" : "amber"
                  }
                >
                  {titleCase(inv.status)}
                </Badge>
              </div>
            </div>
          );
        })}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">No invoices yet.</p>
        )}
      </div>
    </SectionCard>
  );
}

function CreditNotesTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.creditNotes(t, id), [id], {
    key: `merchant-credits-${id}`,
  });
  return (
    <SectionCard title="Credit notes">
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((c) => (
          <div key={c.credit_note_id} className="flex items-center justify-between gap-3 px-5 py-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-primary">
                {c.order_number ?? c.credit_note_id.slice(0, 8)}
              </p>
              <p className="text-xs text-muted">
                {c.reason ?? "Credit note"}
                {c.tracking_number ? ` · ${c.tracking_number}` : ""}
                {c.created_at ? ` · ${shortDate(c.created_at)}` : ""}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold text-primary">{money(c.amount_cents)}</p>
              <Badge tone={c.status === "applied" || c.status === "issued" ? "green" : "slate"}>
                {titleCase(c.status)}
              </Badge>
            </div>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            No credit notes on file. Credits reduce outstanding AR on the statement.
          </p>
        )}
      </div>
    </SectionCard>
  );
}

function ContractsTab({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => merchants.contracts(t, id), [id], {
    key: `merchant-contracts-${id}`,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [terms, setTerms] = useState("NET_30");
  const [value, setValue] = useState(0);
  const [editId, setEditId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState("draft");
  const [editTerms, setEditTerms] = useState("NET_30");
  const [editValue, setEditValue] = useState(0);

  async function createContract() {
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.createContract(token, id, {
        net_terms: terms,
        value_cents: Math.round(Number(value) * 100) || 0,
      });
      void refetch();
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Create failed"));
    } finally {
      setBusy(false);
    }
  }

  async function saveAmend(contractId: string) {
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.updateContract(token, id, contractId, {
        status: editStatus,
        net_terms: editTerms,
        value_cents: Math.round(Number(editValue) * 100) || 0,
      });
      setEditId(null);
      void refetch();
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Update failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <SectionCard title="New contract">
        <div className="grid grid-cols-2 gap-4 p-5">
          <Field label="Net terms">
            <Select value={terms} onChange={(e) => setTerms(e.target.value)}>
              {TERMS.map((t) => (
                <option key={t} value={t}>
                  {titleCase(t)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Value ($)">
            <Input
              type="number"
              step="0.01"
              value={value}
              onChange={(e) => setValue(Number(e.target.value))}
            />
          </Field>
          <div className="col-span-2 flex items-center gap-3">
            <Button onClick={() => void createContract()} disabled={busy}>
              {busy ? "Creating…" : "Create contract"}
            </Button>
            {error && <span className="text-sm text-red-600">{error}</span>}
          </div>
          <p className="col-span-2 text-xs text-muted">
            Requires a linked CRM company (convert lead → merchant). Draft contract is created for
            that company.
          </p>
        </div>
      </SectionCard>
      <SectionCard title="Contracts">
        <div className="divide-y divide-primary/5">
          {(data ?? []).map((c) => (
            <div key={c.id} className="px-5 py-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-primary">{c.contract_number}</p>
                  <p className="text-xs text-muted">
                    {titleCase(c.net_terms)} · {money(c.value_cents)} · expires{" "}
                    {shortDate(c.expiry_date)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={c.status === "active" ? "green" : "slate"}>
                    {titleCase(c.status)}
                  </Badge>
                  <Button
                    variant="outline"
                    className="text-xs"
                    onClick={() => {
                      setEditId(editId === c.id ? null : c.id);
                      setEditStatus(c.status);
                      setEditTerms(c.net_terms);
                      setEditValue((c.value_cents || 0) / 100);
                    }}
                  >
                    {editId === c.id ? "Close" : "Amend"}
                  </Button>
                </div>
              </div>
              {editId === c.id && (
                <div className="mt-3 grid grid-cols-3 gap-3 rounded-xl border border-primary/10 bg-gray-bg/40 p-3">
                  <Field label="Status">
                    <Select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                      {CONTRACT_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {titleCase(s)}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Net terms">
                    <Select value={editTerms} onChange={(e) => setEditTerms(e.target.value)}>
                      {TERMS.map((t) => (
                        <option key={t} value={t}>
                          {titleCase(t)}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Value ($)">
                    <Input
                      type="number"
                      step="0.01"
                      value={editValue}
                      onChange={(e) => setEditValue(Number(e.target.value))}
                    />
                  </Field>
                  <div className="col-span-3">
                    <Button onClick={() => void saveAmend(c.id)} disabled={busy}>
                      {busy ? "Saving…" : "Save amend"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))}
          {(!data || data.length === 0) && (
            <p className="px-5 py-10 text-center text-sm text-muted">No contracts yet.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function ApiTab({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data } = useApiData((t) => merchants.api(t, id), [id, version], {
    key: `merchant-api-${id}-${version}`,
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rateEdits, setRateEdits] = useState<Record<string, string>>({});
  const [openHook, setOpenHook] = useState<string | null>(null);
  const [deliveries, setDeliveries] = useState<
    Array<{
      id: string;
      webhook_id: string;
      status: string;
      attempt: number;
      http_status: number | null;
      error: string | null;
      created_at: string | null;
    }>
  >([]);
  const apiKeys = data?.api_keys ?? [];
  const webhooks = data?.webhooks ?? [];
  const shops = data?.shopify_shops ?? [];

  async function revoke(keyId: string) {
    if (!window.confirm("Revoke this API key? The merchant cannot use it after this.")) return;
    setBusy(keyId);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.revokeApiKey(token, id, keyId);
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Could not revoke that key"));
    } finally {
      setBusy(null);
    }
  }

  async function saveRate(keyId: string) {
    const raw = rateEdits[keyId];
    const rpm = Number(raw);
    if (!Number.isFinite(rpm) || rpm < 10) {
      setError(merchantActionMessage("rate_limit_invalid"));
      return;
    }
    setBusy(`rate-${keyId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.updateApiKeyRateLimit(token, id, keyId, Math.round(rpm));
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Rate limit update failed"));
    } finally {
      setBusy(null);
    }
  }

  async function disableHook(webhookId: string) {
    if (!window.confirm("Disable this webhook? PorterChain will stop posting events to it.")) {
      return;
    }
    setBusy(webhookId);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.disableWebhook(token, id, webhookId);
      setVersion((v) => v + 1);
    } catch (e) {
      setError(
        merchantActionMessage(e instanceof Error ? e.message : "Could not disable that webhook")
      );
    } finally {
      setBusy(null);
    }
  }

  async function loadDeliveries(webhookId: string) {
    if (openHook === webhookId) {
      setOpenHook(null);
      setDeliveries([]);
      return;
    }
    setBusy(`del-${webhookId}`);
    setError(null);
    try {
      const token = await getApiToken();
      const rows = await merchants.webhookDeliveries(token, id, webhookId);
      setDeliveries(rows);
      setOpenHook(webhookId);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Could not load deliveries"));
    } finally {
      setBusy(null);
    }
  }

  async function retryDelivery(deliveryId: string) {
    setBusy(`retry-${deliveryId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.retryWebhookDelivery(token, id, deliveryId);
      if (openHook) {
        const rows = await merchants.webhookDeliveries(token, id, openHook);
        setDeliveries(rows);
      }
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Retry failed"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-5">
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {shops.length > 0 && (
        <SectionCard title={`Shopify (${shops.length})`}>
          <div className="divide-y divide-primary/5">
            {shops.map((s) => (
              <div key={s.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium text-primary">{s.shop_domain}</p>
                  <p className="text-xs text-muted">
                    {s.last_webhook_at
                      ? `Last webhook ${relativeTime(s.last_webhook_at)}`
                      : "No webhooks yet"}
                  </p>
                </div>
                <Badge tone={s.installed ? "green" : "slate"}>
                  {s.installed ? "Connected" : "Uninstalled"}
                </Badge>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
      <div className="grid gap-5 md:grid-cols-2">
        <SectionCard title={`API keys (${apiKeys.length})`}>
          <div className="divide-y divide-primary/5">
            {apiKeys.map((k) => (
              <div key={k.id} className="space-y-2 px-5 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-primary">
                      {k.name}{" "}
                      <Badge tone={k.environment === "production" ? "green" : "slate"}>
                        {titleCase(k.environment)}
                      </Badge>
                      {!k.is_active && (
                        <Badge tone="red" className="ml-1">
                          Revoked
                        </Badge>
                      )}
                    </p>
                    <p className="text-xs text-muted">
                      {k.key_prefix}••• · {k.rate_limit_per_minute}/min · last used{" "}
                      {relativeTime(k.last_used_at)}
                    </p>
                  </div>
                  {k.is_active ? (
                    <Button
                      variant="outline"
                      className="text-xs"
                      disabled={busy === k.id}
                      onClick={() => void revoke(k.id)}
                    >
                      {busy === k.id ? "Revoking…" : "Revoke"}
                    </Button>
                  ) : null}
                </div>
                {k.is_active ? (
                  <div className="flex flex-wrap items-end gap-2">
                    <Field label="Rate / min">
                      <Input
                        type="number"
                        min={10}
                        className="w-28"
                        value={rateEdits[k.id] ?? String(k.rate_limit_per_minute)}
                        onChange={(e) =>
                          setRateEdits((prev) => ({ ...prev, [k.id]: e.target.value }))
                        }
                      />
                    </Field>
                    <Button
                      variant="outline"
                      className="text-xs"
                      disabled={busy === `rate-${k.id}`}
                      onClick={() => void saveRate(k.id)}
                    >
                      {busy === `rate-${k.id}` ? "Saving…" : "Save limit"}
                    </Button>
                  </div>
                ) : null}
              </div>
            ))}
            {apiKeys.length === 0 && (
              <p className="px-5 py-10 text-center text-sm text-muted">No API keys.</p>
            )}
          </div>
        </SectionCard>
        <SectionCard title={`Webhooks (${webhooks.length})`}>
          <div className="divide-y divide-primary/5">
            {webhooks.map((w) => (
              <div key={w.id} className="space-y-2 px-5 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-primary">{w.url}</p>
                    <p className="text-xs text-muted">{w.events.join(", ") || "all events"}</p>
                  </div>
                  <div className="flex shrink-0 flex-col gap-1">
                    <Button
                      variant="outline"
                      className="text-xs"
                      disabled={busy === `del-${w.id}`}
                      onClick={() => void loadDeliveries(w.id)}
                    >
                      {openHook === w.id
                        ? "Hide deliveries"
                        : busy === `del-${w.id}`
                          ? "Loading…"
                          : "Deliveries"}
                    </Button>
                    {w.is_active ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === w.id}
                        onClick={() => void disableHook(w.id)}
                      >
                        {busy === w.id ? "Disabling…" : "Disable"}
                      </Button>
                    ) : (
                      <Badge tone="red">Disabled</Badge>
                    )}
                  </div>
                </div>
                {openHook === w.id && (
                  <div className="rounded-xl border border-primary/10 bg-gray-bg/40">
                    {deliveries.length === 0 ? (
                      <p className="px-3 py-4 text-center text-xs text-muted">No deliveries yet.</p>
                    ) : (
                      deliveries.map((d) => (
                        <div
                          key={d.id}
                          className="flex items-center justify-between gap-2 border-t border-primary/5 px-3 py-2 first:border-t-0"
                        >
                          <div className="min-w-0">
                            <p className="text-xs font-medium text-primary">
                              {titleCase(d.status)}
                              {d.http_status != null ? ` · HTTP ${d.http_status}` : ""} · attempt{" "}
                              {d.attempt}
                            </p>
                            <p className="truncate text-[11px] text-muted">
                              {d.error || relativeTime(d.created_at)}
                            </p>
                          </div>
                          {(d.status === "failed" || d.status === "error") && (
                            <Button
                              variant="outline"
                              className="text-xs"
                              disabled={busy === `retry-${d.id}`}
                              onClick={() => void retryDelivery(d.id)}
                            >
                              {busy === `retry-${d.id}` ? "…" : "Retry"}
                            </Button>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            ))}
            {webhooks.length === 0 && (
              <p className="px-5 py-10 text-center text-sm text-muted">No webhooks.</p>
            )}
          </div>
        </SectionCard>
      </div>
    </div>
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

function serviceAreaFromMerchant(m: MerchantDetail): string {
  const fromProfile =
    typeof m.profile?.service_area === "string" ? m.profile.service_area.trim() : "";
  return fromProfile || m.coverage?.service_area || m.service_area || "Ontario";
}

function zonesFromMerchant(m: MerchantDetail): string {
  return (m.delivery_zones ?? [])
    .map((z) => String(z))
    .filter(Boolean)
    .join(", ");
}

function billingFromMerchant(m: MerchantDetail): BookingAddress {
  const raw = (m.billing_address ?? {}) as Record<string, unknown>;
  return {
    formatted: String(raw.formatted ?? ""),
    postal: typeof raw.postal === "string" ? raw.postal : undefined,
    lat: typeof raw.lat === "number" ? raw.lat : undefined,
    lng: typeof raw.lng === "number" ? raw.lng : undefined,
    placeId: typeof raw.place_id === "string" ? raw.place_id : undefined,
  };
}

function SettingsTab({ m, onSaved }: { m: MerchantDetail; onSaved: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [companyName, setCompanyName] = useState(m.company_name);
  const [legalName, setLegalName] = useState(m.legal_name ?? "");
  const [email, setEmail] = useState(m.email ?? "");
  const [website, setWebsite] = useState(m.website ?? "");
  const [industry, setIndustry] = useState(m.industry ?? "");
  const [terms, setTerms] = useState(m.payment_terms);
  const [creditDollars, setCreditDollars] = useState(
    m.credit_limit_cents != null ? (m.credit_limit_cents / 100).toFixed(2) : ""
  );
  const [cycle, setCycle] = useState(m.billing_cycle || "MONTHLY");
  const [supportTier, setSupportTier] = useState(m.support_tier || "standard");
  const [phone, setPhone] = useState(m.phone ?? "");
  const [hst, setHst] = useState(m.hst_number ?? "");
  const [bn, setBn] = useState(m.business_number ?? "");
  const [taxExempt, setTaxExempt] = useState(Boolean(m.tax_exempt));
  const [taxRegion, setTaxRegion] = useState(m.tax_region || "ON");
  const [stripeOn, setStripeOn] = useState(Boolean(m.stripe_enabled));
  const [codOn, setCodOn] = useState(Boolean(m.cod_enabled));
  const [prefs, setPrefs] = useState<string[]>(m.preferred_vehicles ?? []);
  const [serviceArea, setServiceArea] = useState(() => serviceAreaFromMerchant(m));
  const [zonesText, setZonesText] = useState(() => zonesFromMerchant(m));
  const [billing, setBilling] = useState<BookingAddress>(() => billingFromMerchant(m));
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setCompanyName(m.company_name);
    setLegalName(m.legal_name ?? "");
    setEmail(m.email ?? "");
    setWebsite(m.website ?? "");
    setIndustry(m.industry ?? "");
    setTerms(m.payment_terms);
    setCreditDollars(m.credit_limit_cents != null ? (m.credit_limit_cents / 100).toFixed(2) : "");
    setCycle(m.billing_cycle || "MONTHLY");
    setSupportTier(m.support_tier || "standard");
    setPhone(m.phone ?? "");
    setHst(m.hst_number ?? "");
    setBn(m.business_number ?? "");
    setTaxExempt(Boolean(m.tax_exempt));
    setTaxRegion(m.tax_region || "ON");
    setStripeOn(Boolean(m.stripe_enabled));
    setCodOn(Boolean(m.cod_enabled));
    setPrefs(m.preferred_vehicles ?? []);
    setServiceArea(serviceAreaFromMerchant(m));
    setZonesText(zonesFromMerchant(m));
    setBilling(billingFromMerchant(m));
  }, [m]);

  function togglePref(id: string) {
    setPrefs((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function save() {
    setBusy(true);
    setSaveError(null);
    try {
      const token = await getApiToken();
      const body: Parameters<typeof merchants.update>[2] = {
        company_name: companyName.trim(),
        email: email.trim() || undefined,
        website: website.trim() || undefined,
        industry: industry.trim() || undefined,
        payment_terms: terms,
        credit_limit_cents: Math.round(Number(creditDollars || 0) * 100),
        billing_cycle: cycle,
        support_tier: supportTier as "standard" | "priority" | "enterprise",
        preferred_vehicles: prefs,
        delivery_zones: zonesText
          .split(/[,\n]/)
          .map((code) => code.trim())
          .filter(Boolean),
        service_area: serviceArea.trim(),
        phone: phone.trim(),
        stripe_enabled: stripeOn,
        cod_enabled: codOn,
        billing_address: billing.formatted.trim()
          ? {
              formatted: billing.formatted.trim(),
              postal: billing.postal,
              lat: billing.lat,
              lng: billing.lng,
              place_id: billing.placeId,
            }
          : {},
      };
      if ((legalName.trim() || "") !== (m.legal_name || "")) {
        body.legal_name = legalName.trim();
      }
      if (hst.trim() !== (m.hst_number || "")) {
        body.hst_number = hst.trim();
      }
      if ((bn.trim() || "") !== (m.business_number || "")) {
        body.business_number = bn.trim();
      }
      if (taxExempt !== Boolean(m.tax_exempt)) {
        body.tax_exempt = taxExempt;
      }
      if ((taxRegion.trim() || "ON") !== (m.tax_region || "ON")) {
        body.tax_region = taxRegion.trim() || "ON";
      }
      await merchants.update(token, m.id, body);
      setSaved(true);
      onSaved();
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setSaved(false);
      setSaveError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted">
        Org config for this company. Pricing lives on the Pricing tab. Seats live under People.
      </p>
      <SectionCard title="Company identity">
        <div className="grid grid-cols-2 gap-4 p-5">
          <div className="col-span-2">
            <Field label="Company name">
              <Input value={companyName} onChange={(e) => setCompanyName(e.target.value)} />
            </Field>
          </div>
          <Field label="Legal name">
            <Input value={legalName} onChange={(e) => setLegalName(e.target.value)} />
          </Field>
          <Field label="Company email">
            <Input value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Website">
            <Input value={website} onChange={(e) => setWebsite(e.target.value)} />
          </Field>
          <Field label="Industry">
            <Input value={industry} onChange={(e) => setIndustry(e.target.value)} />
          </Field>
          <Field label="Phone">
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
          </Field>
          <div className="col-span-2">
            <p className="mb-1 text-xs font-medium text-primary/70">Billing address</p>
            <GoogleMapsProvider>
              <AddressAutocompleteInput
                id={`admin-merchant-billing-${m.id}`}
                value={billing.formatted}
                onChange={(formatted) => setBilling({ ...billing, formatted })}
                onPlaceSelect={setBilling}
                apiKey={publicEnv.googleMapsApiKey}
                placeholder="Ontario billing address"
                fallbackClassName="w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
              />
            </GoogleMapsProvider>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Commercial terms">
        <div className="grid grid-cols-2 gap-4 p-5">
          <Field label="Payment terms">
            <Select value={terms} onChange={(e) => setTerms(e.target.value)}>
              {TERMS.map((t) => (
                <option key={t} value={t}>
                  {titleCase(t)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Billing cycle">
            <Select value={cycle} onChange={(e) => setCycle(e.target.value)}>
              {BILLING_CYCLES.map((c) => (
                <option key={c} value={c}>
                  {titleCase(c)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Support tier">
            <Select value={supportTier} onChange={(e) => setSupportTier(e.target.value)}>
              {SUPPORT_TIERS.map((tier) => (
                <option key={tier} value={tier}>
                  {titleCase(tier)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Credit limit (CAD)">
            <Input
              type="number"
              step="0.01"
              value={creditDollars}
              onChange={(e) => setCreditDollars(e.target.value)}
            />
          </Field>
          <div className="col-span-2 space-y-3">
            <label className="flex items-center gap-2 text-sm text-primary">
              <input
                type="checkbox"
                checked={stripeOn}
                onChange={(e) => setStripeOn(e.target.checked)}
              />
              Stripe checkout enabled (card / IMMEDIATE path)
            </label>
            <label className="flex items-center gap-2 text-sm text-primary">
              <input type="checkbox" checked={codOn} onChange={(e) => setCodOn(e.target.checked)} />
              Cash on delivery (requires Stripe Connect on the merchant billing page)
            </label>
            {m.stripe_connect_account_id ? (
              <p className="text-xs text-muted">Connect account {m.stripe_connect_account_id}</p>
            ) : (
              <p className="text-xs text-muted">
                No Connect account yet. Merchant links it under{" "}
                <a
                  href={`${getSystemLinks().find((l) => l.id === "merchant")?.href ?? "http://localhost:3001"}/billing?tab=cod`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-secondary underline"
                >
                  Portal Billing → COD
                </a>
                .
              </p>
            )}
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Tax & legal">
        <div className="grid grid-cols-2 gap-4 p-5">
          <Field label="HST / GST number">
            <Input
              value={hst}
              onChange={(e) => setHst(e.target.value)}
              placeholder="123456789RT0001"
            />
          </Field>
          <Field label="Business number">
            <Input value={bn} onChange={(e) => setBn(e.target.value)} placeholder="123456789" />
          </Field>
          <Field label="Tax region">
            <Select value={taxRegion} onChange={(e) => setTaxRegion(e.target.value)}>
              {CA_TAX_REGIONS.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </Select>
          </Field>
          <label className="flex items-center gap-2 text-sm text-primary">
            <input
              type="checkbox"
              checked={taxExempt}
              onChange={(e) => setTaxExempt(e.target.checked)}
            />
            Tax exempt
          </label>
        </div>
      </SectionCard>
      <SectionCard title="Coverage we send">
        <div className="grid grid-cols-2 gap-4 p-5">
          <div className="col-span-2">
            <Field label="Service area">
              <Input
                value={serviceArea}
                onChange={(e) => setServiceArea(e.target.value)}
                placeholder="Ontario"
              />
            </Field>
            <p className="mt-1 text-xs text-muted">
              Shown read-only in the merchant portal. Pickup and drop-off stay Ontario (K, L, M, N,
              P).
            </p>
          </div>
          <div className="col-span-2">
            <Field label="Delivery zone codes">
              <Input
                value={zonesText}
                onChange={(e) => setZonesText(e.target.value)}
                placeholder="gta_core, gta_west"
              />
            </Field>
            <p className="mt-1 text-xs text-muted">Comma-separated pricing zone codes.</p>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Assigned vehicles we send">
        <div className="flex flex-wrap gap-2 p-5">
          {RETAIL_VEHICLE_OPTIONS.map((v) => {
            const on = prefs.includes(v);
            return (
              <button
                key={v}
                type="button"
                onClick={() => togglePref(v)}
                className={cn(
                  "rounded-xl border px-3 py-1.5 text-sm font-medium transition",
                  on
                    ? "border-secondary bg-secondary/10 text-secondary"
                    : "border-primary/15 text-muted hover:bg-gray-bg"
                )}
              >
                {vehicleClassLabel(v)}
              </button>
            );
          })}
          <p className="w-full text-xs text-muted">
            Vehicles PorterChain sends for this merchant. They book a class for the job — they do
            not manage a fleet. Soft-ranks booking recommendations; must match the retail catalog.
          </p>
        </div>
      </SectionCard>
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={save} disabled={busy}>
          Save changes
        </Button>
        {saved && <span className="text-sm text-green-600">Saved</span>}
        {saveError && <span className="text-sm text-red-600">{saveError}</span>}
        {m.tax_legal_meta?.updated_at ? (
          <span className="text-xs text-muted">
            Tax & legal last updated by {m.tax_legal_meta.updated_by || "someone"}{" "}
            {dateTime(m.tax_legal_meta.updated_at)}
          </span>
        ) : null}
      </div>
      <MerchantBillingContactsCard id={m.id} />
      {(m.documents?.length ?? 0) > 0 && (
        <SectionCard title="Documents on file">
          <ul className="divide-y divide-primary/5">
            {m.documents?.map((doc) => (
              <li key={doc.id} className="flex justify-between gap-3 px-5 py-3 text-sm">
                <span>
                  <span className="font-medium text-primary">{doc.name}</span>
                  <span className="ml-2 text-muted">{doc.type || "other"}</span>
                  {doc.reference ? <span className="ml-2 text-muted">{doc.reference}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        </SectionCard>
      )}
      <SubsidiariesCard merchantId={m.id} parentId={m.parent_merchant_id} onChanged={onSaved} />
      <MerchantPrivacyCard id={m.id} />
      <DangerZone m={m} onSaved={onSaved} />
    </div>
  );
}

function SubsidiariesCard({
  merchantId,
  parentId,
  onChanged,
}: {
  merchantId: string;
  parentId?: string | null;
  onChanged?: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => merchants.subsidiaries(t, merchantId), [merchantId], {
    key: `merchant-subsidiaries-${merchantId}`,
  });
  const { data: parentDetail } = useApiData(
    (t) => (parentId ? merchants.detail(t, parentId) : Promise.resolve(null)),
    [parentId],
    { key: `merchant-parent-${parentId || "none"}`, enabled: Boolean(parentId) }
  );
  const [parentInput, setParentInput] = useState(parentId ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rows = data ?? [];

  useEffect(() => {
    setParentInput(parentId ?? "");
  }, [parentId]);

  async function saveParent(next: string | null) {
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      // Empty string clears parent (API treats null as "omit field").
      await merchants.update(token, merchantId, {
        parent_merchant_id: next && next.trim() ? next.trim() : "",
      });
      void refetch();
      onChanged?.();
    } catch (e) {
      setError(merchantActionMessage(e, "Could not update parent company"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SectionCard title="Related companies">
      <div className="space-y-3 px-5 py-4 text-sm">
        <div className="space-y-2">
          <p className="text-xs text-muted">Parent company (UUID). Clear to detach.</p>
          {parentId ? (
            <p className="text-muted">
              Current parent{" "}
              <Link href={`/merchants/${parentId}`} className="font-medium text-secondary">
                {(parentDetail as MerchantDetail | null)?.company_name ||
                  `${parentId.slice(0, 8)}…`}
              </Link>
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-2">
            <Input
              value={parentInput}
              onChange={(e) => setParentInput(e.target.value)}
              placeholder="Parent merchant id"
              className="min-w-[16rem] flex-1"
            />
            <Button
              disabled={busy || !parentInput.trim() || parentInput.trim() === merchantId}
              onClick={() => void saveParent(parentInput.trim())}
            >
              {busy ? "Saving…" : "Attach"}
            </Button>
            {parentId ? (
              <Button variant="outline" disabled={busy} onClick={() => void saveParent(null)}>
                Clear
              </Button>
            ) : null}
          </div>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </div>
        {rows.map((row) => (
          <Link
            key={row.merchant_id}
            href={`/merchants/${row.merchant_id}`}
            className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-gray-bg"
          >
            <span className="font-medium text-primary">{row.company_name}</span>
            <span className="text-xs text-muted">{titleCase(row.status)}</span>
          </Link>
        ))}
        {!parentId && rows.length === 0 ? (
          <p className="text-xs text-muted">No subsidiaries linked yet.</p>
        ) : null}
      </div>
    </SectionCard>
  );
}

function DangerZone({ m, onSaved }: { m: MerchantDetail; onSaved: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const closed = m.status === "CLOSED";
  const owed = m.outstanding_balance_cents || 0;

  async function run(action: string, fn: () => Promise<void>) {
    setBusy(action);
    setError(null);
    try {
      await fn();
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <SectionCard title="Close or convert">
      <div className="space-y-3 p-5 text-sm">
        <p className="text-muted">
          Closing turns off the merchant portal. Orders and invoices stay on this company file.
          Convert opens a retail customer record for the owner email without moving shipment
          history.
        </p>
        {owed > 0 && (
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-900">
            Outstanding AR: {money(owed)}. Close is blocked until this is collected. Convert can
            write it off.
          </p>
        )}
        {error && <p className="text-red-600">{error}</p>}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            disabled={closed || busy !== null}
            onClick={() => {
              const reason = window.prompt("Reason for closing this merchant account?");
              if (!reason?.trim()) return;
              void run("close", async () => {
                const token = await getApiToken();
                await merchants.close(token, m.id, reason.trim());
              });
            }}
          >
            {busy === "close" ? "Closing…" : "Close account"}
          </Button>
          <Button
            variant="outline"
            disabled={closed || busy !== null}
            onClick={() => {
              if (
                !window.confirm(
                  "Convert this merchant to a retail customer? Portal seats will be revoked. Historical orders stay on this merchant."
                )
              ) {
                return;
              }
              const writeOff =
                owed > 0 &&
                window.confirm(`Write off ${money(owed)} outstanding AR so convert can proceed?`);
              if (owed > 0 && !writeOff) return;
              void run("convert", async () => {
                const token = await getApiToken();
                await merchants.convertToCustomer(token, m.id, {
                  owner_email: m.email || undefined,
                  write_off_ar: Boolean(writeOff),
                });
              });
            }}
          >
            {busy === "convert" ? "Converting…" : "Convert to retail customer"}
          </Button>
          {closed && (
            <Button
              variant="outline"
              disabled={busy !== null}
              onClick={() => {
                if (
                  !window.confirm(
                    "Erase contact details for this closed merchant? Order numbers and invoice amounts are kept."
                  )
                ) {
                  return;
                }
                void run("privacy", async () => {
                  const token = await getApiToken();
                  await merchants.executePrivacy(token, m.id);
                });
              }}
            >
              {busy === "privacy" ? "Erasing…" : "Execute privacy erasure"}
            </Button>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
