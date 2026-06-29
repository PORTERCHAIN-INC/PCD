"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Activity as ActivityIcon,
  ArrowLeft,
  Boxes,
  Building2,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Contact as ContactIcon,
  CreditCard,
  FileSignature,
  Globe,
  Info,
  KeyRound,
  MapPin,
  Package,
  Receipt,
  Rocket,
  Settings as SettingsIcon,
  Sparkles,
  Users,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchants, healthTone, type MerchantDetail } from "@/lib/merchants";
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
};
const RISK_TONE: Record<string, string> = { low: "green", medium: "amber", high: "red" };
const TERMS = ["IMMEDIATE", "NET_7", "NET_15", "NET_30", "NET_45", "CUSTOM"];

type TabId =
  | "overview"
  | "contacts"
  | "locations"
  | "orders"
  | "invoices"
  | "contracts"
  | "pricing"
  | "api"
  | "team"
  | "activities"
  | "tasks"
  | "timeline"
  | "analytics"
  | "settings";

const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "overview", label: "Overview", icon: Info },
  { id: "contacts", label: "Contacts", icon: ContactIcon },
  { id: "locations", label: "Locations", icon: MapPin },
  { id: "orders", label: "Orders", icon: Package },
  { id: "invoices", label: "Invoices", icon: Receipt },
  { id: "contracts", label: "Contracts", icon: FileSignature },
  { id: "pricing", label: "Pricing", icon: CreditCard },
  { id: "api", label: "API", icon: KeyRound },
  { id: "team", label: "Team", icon: Users },
  { id: "activities", label: "Activities", icon: ActivityIcon },
  { id: "tasks", label: "Tasks", icon: ClipboardList },
  { id: "timeline", label: "Timeline", icon: CalendarClock },
  { id: "analytics", label: "Analytics", icon: Boxes },
  { id: "settings", label: "Settings", icon: SettingsIcon },
];

export default function MerchantDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const [tab, setTab] = useState<TabId>("overview");
  const [busy, setBusy] = useState(false);

  const { data: m, error } = useApiData((t) => merchants.detail(t, id), [id, version]);
  const refresh = () => setVersion((v) => v + 1);

  async function lifecycle(action: "approve" | "suspend") {
    setBusy(true);
    try {
      const token = await getApiToken();
      if (action === "approve") await merchants.approve(token, id);
      else await merchants.suspend(token, id);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!m) return <Spinner label="Loading merchant…" />;

  return (
    <div className="space-y-5">
      <button
        onClick={() => router.push("/merchants")}
        className="flex items-center gap-1.5 text-sm text-muted hover:text-primary"
      >
        <ArrowLeft className="h-4 w-4" /> All merchants
      </button>

      {/* Header */}
      <div className="rounded-2xl border border-primary/10 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-2xl bg-secondary/10 text-secondary">
              {m.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={m.logo_url} alt="" className="h-full w-full object-cover" />
              ) : (
                <Building2 className="h-7 w-7" />
              )}
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold text-primary">{m.company_name}</h1>
                <Badge tone={STATUS_TONE[m.status] ?? "slate"}>{titleCase(m.status)}</Badge>
                {m.api_connected && <Badge tone="green">API</Badge>}
              </div>
              <p className="mt-0.5 text-sm text-muted">
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
          <div className="flex items-center gap-2">
            {m.status !== "ACTIVE" && (
              <Button onClick={() => lifecycle("approve")} disabled={busy}>
                <Rocket className="h-4 w-4" /> Approve
              </Button>
            )}
            {m.status !== "SUSPENDED" && (
              <Button variant="outline" onClick={() => lifecycle("suspend")} disabled={busy}>
                Suspend
              </Button>
            )}
          </div>
        </div>

        {/* Metric tiles + health + AI */}
        <div className="mt-5 grid gap-3 lg:grid-cols-4">
          <HealthCard score={m.health} />
          <Metric
            label="Monthly revenue"
            value={money(m.metrics.monthly_revenue_cents)}
            sub={`${m.metrics.monthly_orders} orders / 30d`}
          />
          <Metric
            label="Outstanding"
            value={money(m.metrics.outstanding_balance_cents)}
            sub={
              m.metrics.overdue_balance_cents > 0
                ? `${money(m.metrics.overdue_balance_cents)} overdue`
                : "On track"
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
      <div className="sticky top-0 z-10 flex gap-1 overflow-x-auto rounded-2xl border border-primary/10 bg-white/90 p-1.5 backdrop-blur">
        {TABS.map(({ id: tid, label, icon: Icon }) => (
          <button
            key={tid}
            onClick={() => setTab(tid)}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
              tab === tid ? "bg-secondary text-white" : "text-primary/70 hover:bg-gray-bg"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      <div>
        {tab === "overview" && <OverviewTab m={m} onGoto={setTab} />}
        {tab === "contacts" && <ContactsTab id={id} />}
        {tab === "locations" && <LocationsTab id={id} />}
        {tab === "orders" && <OrdersTab id={id} />}
        {tab === "invoices" && <InvoicesTab id={id} />}
        {tab === "contracts" && <ContractsTab id={id} />}
        {tab === "pricing" && <PricingTab m={m} />}
        {tab === "api" && <ApiTab id={id} />}
        {tab === "team" && <TeamTab id={id} />}
        {tab === "activities" &&
          (m.company_id ? (
            <ActivityTimeline entityType="company" entityId={m.company_id} />
          ) : (
            <ReadActivities id={id} />
          ))}
        {tab === "tasks" &&
          (m.company_id ? (
            <EntityTasks entityType="company" entityId={m.company_id} companyId={m.company_id} />
          ) : (
            <p className="py-10 text-center text-sm text-muted">
              Tasks available once a CRM company is linked.
            </p>
          ))}
        {tab === "timeline" && <TimelineTab id={id} />}
        {tab === "analytics" && <AnalyticsTab id={id} />}
        {tab === "settings" && <SettingsTab m={m} onSaved={refresh} />}
      </div>
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
    <div className="rounded-xl border border-primary/10 p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-xl font-bold text-primary">{value}</p>
      {sub && <p className={cn("text-xs", danger ? "text-red-600" : "text-muted")}>{sub}</p>}
    </div>
  );
}

function HealthCard({ score }: { score: number }) {
  const color = score >= 70 ? "#16a34a" : score >= 40 ? "#f59e0b" : "#dc2626";
  return (
    <div className="flex items-center gap-4 rounded-xl border border-primary/10 p-4">
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
  return (
    <div className="mt-4 rounded-xl border border-secondary/20 bg-secondary/5 p-4">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
        <Sparkles className="h-4 w-4 text-secondary" /> AI insights
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge tone={RISK_TONE[ai.risk_score]}>Risk: {titleCase(ai.risk_score)}</Badge>
        <Badge tone={RISK_TONE[ai.payment_risk]}>Payment: {titleCase(ai.payment_risk)}</Badge>
        <Badge tone={RISK_TONE[ai.renewal_risk]}>Renewal: {titleCase(ai.renewal_risk)}</Badge>
        <Badge tone="sky">Trend: {titleCase(ai.revenue_trend)}</Badge>
        <Badge tone="violet">Forecast: {money(ai.predicted_monthly_revenue_cents)}/mo</Badge>
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

function OverviewTab({ m, onGoto }: { m: MerchantDetail; onGoto: (t: TabId) => void }) {
  const a = m.billing_address as Record<string, string>;
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <SectionCard title="Business details" className="lg:col-span-2">
        <dl className="grid grid-cols-2 gap-4 p-5 md:grid-cols-3">
          <Detail label="Legal name" value={m.legal_name} />
          <Detail label="Industry" value={m.industry} />
          <Detail label="Email" value={m.email} />
          <Detail label="Phone" value={m.phone} />
          <Detail label="HST number" value={m.hst_number} />
          <Detail label="Business number" value={m.business_number} />
          <Detail label="Payment terms" value={titleCase(m.payment_terms)} />
          <Detail
            label="Credit limit"
            value={m.credit_limit_cents != null ? money(m.credit_limit_cents) : null}
          />
          <Detail label="Service area" value={m.service_area} />
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
            onClick={() => onGoto("contacts")}
          />
          <QuickRow
            label="Locations"
            value={String(m.counts.locations ?? 0)}
            onClick={() => onGoto("locations")}
          />
          <QuickRow
            label="Team members"
            value={String(m.counts.users ?? 0)}
            onClick={() => onGoto("team")}
          />
          <QuickRow
            label="API keys"
            value={String(m.counts.api_keys ?? 0)}
            onClick={() => onGoto("api")}
          />
          <QuickRow
            label="Open tasks"
            value={String(m.counts.open_tasks ?? 0)}
            onClick={() => onGoto("tasks")}
          />
          <QuickRow
            label="Contract"
            value={titleCase(m.contract_status)}
            onClick={() => onGoto("contracts")}
          />
        </div>
      </SectionCard>
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

function ContactsTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.contacts(t, id), [id]);
  return (
    <SectionCard title={`Contacts (${data?.length ?? 0})`}>
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((c) => (
          <div key={c.id} className="flex items-center justify-between px-5 py-3">
            <div>
              <p className="text-sm font-medium text-primary">
                {c.first_name} {c.last_name} {c.is_primary && <Badge tone="blue">Primary</Badge>}
              </p>
              <p className="text-xs text-muted">
                {c.designation ?? "—"} · {c.email ?? c.phone ?? ""}
              </p>
            </div>
            <div className="flex flex-wrap gap-1">
              {c.roles.slice(0, 3).map((r) => (
                <Badge key={r} tone="slate">
                  {titleCase(r)}
                </Badge>
              ))}
            </div>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            No contacts. Add them from the CRM company.
          </p>
        )}
      </div>
    </SectionCard>
  );
}

function LocationsTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.locations(t, id), [id]);
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title={`Addresses (${data?.addresses.length ?? 0})`}>
        <div className="divide-y divide-primary/5">
          {(data?.addresses ?? []).map((a) => (
            <div key={a.id} className="px-5 py-3">
              <p className="text-sm font-medium text-primary">
                {a.label} {a.is_default && <Badge tone="blue">Default</Badge>}
              </p>
              <p className="text-xs text-muted">
                {titleCase(a.address_type)} · {a.formatted}
              </p>
            </div>
          ))}
          {(!data || data.addresses.length === 0) && (
            <p className="px-5 py-10 text-center text-sm text-muted">No saved locations.</p>
          )}
        </div>
      </SectionCard>
      <SectionCard title={`Recipients (${data?.recipients.length ?? 0})`}>
        <div className="divide-y divide-primary/5">
          {(data?.recipients ?? []).map((r) => (
            <div key={r.id} className="px-5 py-3">
              <p className="text-sm font-medium text-primary">{r.name}</p>
              <p className="text-xs text-muted">
                {r.company ?? ""} · {r.email ?? r.phone ?? ""}
              </p>
            </div>
          ))}
          {(!data || data.recipients.length === 0) && (
            <p className="px-5 py-10 text-center text-sm text-muted">No recipients.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function OrdersTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.orders(t, id), [id]);
  return (
    <SectionCard title={`Orders (${data?.length ?? 0})`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
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
            {(data ?? []).map((o) => (
              <tr key={o.id} className="border-b border-primary/5">
                <td className="px-4 py-2 font-medium text-primary">{o.order_number}</td>
                <td className="px-4 py-2">
                  <Badge tone="sky">{titleCase(o.state)}</Badge>
                </td>
                <td className="px-4 py-2">{money(o.amount_cents)}</td>
                <td className="px-4 py-2">{shortDate(o.scheduled_at)}</td>
                <td className="px-4 py-2">{shortDate(o.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">No orders yet.</p>
        )}
      </div>
    </SectionCard>
  );
}

function InvoicesTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.invoices(t, id), [id]);
  const outstanding = (data ?? [])
    .filter((i) => i.status !== "paid" && i.status !== "void")
    .reduce((s, i) => s + i.total_cents, 0);
  return (
    <SectionCard
      title="Invoices"
      action={
        <span className="text-sm text-muted">
          Outstanding <span className="font-bold text-primary">{money(outstanding)}</span>
        </span>
      }
    >
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((inv) => (
          <div key={inv.id} className="flex items-center justify-between px-5 py-3">
            <div>
              <p className="text-sm font-medium text-primary">{inv.invoice_number}</p>
              <p className="text-xs text-muted">
                {money(inv.total_cents)} · {titleCase(inv.net_terms)} · due{" "}
                {shortDate(inv.due_date)}
              </p>
            </div>
            <Badge
              tone={inv.status === "paid" ? "green" : inv.status === "overdue" ? "red" : "amber"}
            >
              {titleCase(inv.status)}
            </Badge>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">No invoices yet.</p>
        )}
      </div>
    </SectionCard>
  );
}

function ContractsTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.contracts(t, id), [id]);
  return (
    <SectionCard title="Contracts">
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((c) => (
          <div key={c.id} className="flex items-center justify-between px-5 py-3">
            <div>
              <p className="text-sm font-medium text-primary">{c.contract_number}</p>
              <p className="text-xs text-muted">
                {titleCase(c.net_terms)} · {money(c.value_cents)} · expires{" "}
                {shortDate(c.expiry_date)}
              </p>
            </div>
            <Badge tone={c.status === "active" ? "green" : "slate"}>{titleCase(c.status)}</Badge>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">No contracts yet.</p>
        )}
      </div>
    </SectionCard>
  );
}

function PricingTab({ m }: { m: MerchantDetail }) {
  const cfg = m.pricing_config ?? {};
  const entries = Object.entries(cfg);
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title="Pricing configuration">
        <dl className="grid grid-cols-2 gap-4 p-5">
          <Detail label="Payment terms" value={titleCase(m.payment_terms)} />
          <Detail
            label="Credit limit"
            value={m.credit_limit_cents != null ? money(m.credit_limit_cents) : null}
          />
          <Detail
            label="Preferred vehicles"
            value={(m.preferred_vehicles ?? []).map(titleCase).join(", ") || null}
          />
          <Detail
            label="Delivery zones"
            value={((m.delivery_zones as string[]) ?? []).join(", ") || null}
          />
        </dl>
        {entries.length > 0 && (
          <div className="border-t border-primary/10 p-5">
            <p className="mb-2 text-xs font-semibold uppercase text-muted">Contract rates</p>
            <dl className="grid grid-cols-2 gap-3">
              {entries.map(([k, v]) => (
                <Detail key={k} label={titleCase(k)} value={String(v)} />
              ))}
            </dl>
          </div>
        )}
      </SectionCard>
      <SectionCard title="Notes">
        <p className="p-5 text-sm text-muted">
          Contract pricing, zones, vehicle rates, fuel surcharge and taxes are owned by the
          Porterchain pricing engine. Manage global tariffs under Pricing; merchant-specific
          overrides live in the linked contract.
        </p>
      </SectionCard>
    </div>
  );
}

function ApiTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.api(t, id), [id]);
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title={`API keys (${data?.api_keys.length ?? 0})`}>
        <div className="divide-y divide-primary/5">
          {(data?.api_keys ?? []).map((k) => (
            <div key={k.id} className="px-5 py-3">
              <p className="text-sm font-medium text-primary">
                {k.name}{" "}
                <Badge tone={k.environment === "production" ? "green" : "slate"}>
                  {titleCase(k.environment)}
                </Badge>
              </p>
              <p className="text-xs text-muted">
                {k.key_prefix}••• · {k.rate_limit_per_minute}/min · last used{" "}
                {relativeTime(k.last_used_at)}
              </p>
            </div>
          ))}
          {(!data || data.api_keys.length === 0) && (
            <p className="px-5 py-10 text-center text-sm text-muted">No API keys.</p>
          )}
        </div>
      </SectionCard>
      <SectionCard title={`Webhooks (${data?.webhooks.length ?? 0})`}>
        <div className="divide-y divide-primary/5">
          {(data?.webhooks ?? []).map((w) => (
            <div key={w.id} className="px-5 py-3">
              <p className="truncate text-sm font-medium text-primary">{w.url}</p>
              <p className="text-xs text-muted">{w.events.join(", ") || "all events"}</p>
            </div>
          ))}
          {(!data || data.webhooks.length === 0) && (
            <p className="px-5 py-10 text-center text-sm text-muted">No webhooks.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function TeamTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.team(t, id), [id]);
  return (
    <SectionCard title={`Team (${data?.length ?? 0})`}>
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((u) => (
          <div key={u.id} className="flex items-center justify-between px-5 py-3">
            <div>
              <p className="text-sm font-medium text-primary">{u.email}</p>
              <p className="text-xs text-muted">{titleCase(u.role)}</p>
            </div>
            <Badge tone={u.is_active ? "green" : "slate"}>
              {u.is_active ? "Active" : "Inactive"}
            </Badge>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">No team members yet.</p>
        )}
      </div>
    </SectionCard>
  );
}

function ReadActivities({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.activities(t, id), [id]);
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
  const { data } = useApiData((t) => merchants.timeline(t, id), [id]);
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
  const { data } = useApiData((t) => merchants.analytics(t, id), [id]);
  if (!data) return <Spinner />;
  const maxRev = Math.max(1, ...data.revenue_by_month.map((r) => r.revenue_cents));
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <SectionCard title="Revenue by month" className="lg:col-span-2">
        <div className="space-y-3 p-5">
          {data.revenue_by_month.map((r) => (
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
          {data.revenue_by_month.length === 0 && (
            <p className="py-6 text-center text-sm text-muted">No order history yet.</p>
          )}
        </div>
      </SectionCard>
      <SectionCard title="Top destinations">
        <div className="divide-y divide-primary/5">
          {data.top_destinations.map((d) => (
            <div key={d.city} className="flex items-center justify-between px-5 py-3 text-sm">
              <span className="text-primary">{d.city}</span>
              <span className="font-semibold text-primary">{d.orders}</span>
            </div>
          ))}
          {data.top_destinations.length === 0 && (
            <p className="px-5 py-8 text-center text-sm text-muted">No destinations yet.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function SettingsTab({ m, onSaved }: { m: MerchantDetail; onSaved: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [terms, setTerms] = useState(m.payment_terms);
  const [credit, setCredit] = useState(m.credit_limit_cents ?? 0);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  async function save() {
    setBusy(true);
    try {
      const token = await getApiToken();
      await merchants.update(token, m.id, {
        payment_terms: terms,
        credit_limit_cents: Number(credit) || 0,
      });
      setSaved(true);
      onSaved();
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setBusy(false);
    }
  }

  return (
    <SectionCard title="Billing & terms">
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
        <Field label="Credit limit (cents)">
          <Input type="number" value={credit} onChange={(e) => setCredit(Number(e.target.value))} />
        </Field>
        <div className="col-span-2 flex items-center gap-3">
          <Button onClick={save} disabled={busy}>
            Save changes
          </Button>
          {saved && <span className="text-sm text-green-600">Saved</span>}
        </div>
      </div>
    </SectionCard>
  );
}
