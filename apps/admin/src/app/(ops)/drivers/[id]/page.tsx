"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Activity as ActivityIcon,
  AlertTriangle,
  ArrowLeft,
  Boxes,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  CreditCard,
  FileText,
  Gauge,
  IdCard,
  Info,
  Mail,
  Package,
  Send,
  ShieldCheck,
  Sparkles,
  Star,
  Truck,
  Wallet,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { drivers, type DriverDetail } from "@/lib/drivers";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { EntityTasks } from "@/components/crm/EntityTasks";
import { Badge, Button, SectionCard, Spinner } from "@/components/crm/primitives";
import { money, shortDate, relativeTime, titleCase, dateTime } from "@/lib/crmFormat";

const STATUS_TONE: Record<string, string> = {
  APPROVED: "green",
  PENDING: "amber",
  SUSPENDED: "red",
  REJECTED: "slate",
};
const AVAIL_TONE: Record<string, string> = {
  online: "green",
  offline: "slate",
  busy: "amber",
  break: "sky",
  vacation: "violet",
};
const RISK_TONE: Record<string, string> = { low: "green", medium: "amber", high: "red" };

type TabId =
  | "overview"
  | "identity"
  | "documents"
  | "vehicles"
  | "orders"
  | "performance"
  | "wallet"
  | "incidents"
  | "activities"
  | "tasks"
  | "timeline"
  | "analytics"
  | "settings";

const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "overview", label: "Overview", icon: Info },
  { id: "identity", label: "Identity", icon: IdCard },
  { id: "documents", label: "Documents", icon: FileText },
  { id: "vehicles", label: "Vehicles", icon: Truck },
  { id: "orders", label: "Orders", icon: Package },
  { id: "performance", label: "Performance", icon: Gauge },
  { id: "wallet", label: "Wallet & Payouts", icon: Wallet },
  { id: "incidents", label: "Incidents", icon: AlertTriangle },
  { id: "activities", label: "Activities", icon: ActivityIcon },
  { id: "tasks", label: "Tasks", icon: ClipboardList },
  { id: "timeline", label: "Timeline", icon: CalendarClock },
  { id: "analytics", label: "Analytics", icon: Boxes },
  { id: "settings", label: "Settings", icon: ShieldCheck },
];

export default function DriverDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const [tab, setTab] = useState<TabId>("overview");
  const [busy, setBusy] = useState(false);

  const { data: d, error } = useApiData((t) => drivers.detail(t, id), [id, version]);
  const refresh = () => setVersion((v) => v + 1);

  async function lifecycle(action: "approve" | "suspend") {
    setBusy(true);
    try {
      const token = await getApiToken();
      if (action === "approve") await drivers.approve(token, id);
      else await drivers.suspend(token, id);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!d) return <Spinner label="Loading driver…" />;

  return (
    <div className="space-y-5">
      <button
        onClick={() => router.push("/drivers")}
        className="flex items-center gap-1.5 text-sm text-muted hover:text-primary"
      >
        <ArrowLeft className="h-4 w-4" /> All drivers
      </button>

      <div className="rounded-2xl border border-primary/10 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <span className="relative flex h-14 w-14 items-center justify-center overflow-hidden rounded-2xl bg-secondary/10 text-base font-semibold text-secondary">
              {d.photo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={d.photo_url} alt="" className="h-full w-full object-cover" />
              ) : (
                d.full_name
                  .split(" ")
                  .map((p) => p[0])
                  .slice(0, 2)
                  .join("")
              )}
              {d.is_online && (
                <span className="absolute -bottom-0.5 -right-0.5 h-4 w-4 rounded-full border-2 border-white bg-green-500" />
              )}
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold text-primary">{d.full_name}</h1>
                <Badge tone={STATUS_TONE[d.status] ?? "slate"}>{titleCase(d.status)}</Badge>
                <Badge tone={AVAIL_TONE[d.availability] ?? "slate"}>
                  {titleCase(d.availability)}
                </Badge>
                {d.rating != null && (
                  <span className="inline-flex items-center gap-1 text-sm font-medium text-primary">
                    <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                    {d.rating.toFixed(1)}
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-sm text-muted">
                {d.vehicle ?? "No vehicle"}
                {d.vehicle_type ? ` · ${titleCase(d.vehicle_type)}` : ""}
                {d.city ? ` · ${[d.city, d.province].filter(Boolean).join(", ")}` : ""} · {d.email}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {d.status !== "APPROVED" && (
              <Button onClick={() => lifecycle("approve")} disabled={busy}>
                <CheckCircle2 className="h-4 w-4" /> Approve
              </Button>
            )}
            {d.status !== "SUSPENDED" && (
              <Button variant="outline" onClick={() => lifecycle("suspend")} disabled={busy}>
                Suspend
              </Button>
            )}
          </div>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-4">
          <HealthCard score={d.health} />
          <Metric
            label="Orders today"
            value={String(d.metrics.orders_today)}
            sub={`${d.metrics.completed_today} completed · ${d.metrics.in_progress} active`}
          />
          <Metric
            label="Earnings (7d)"
            value={money(d.metrics.weekly_earnings_cents)}
            sub={`Wallet ${money(d.metrics.wallet_balance_cents)}`}
          />
          <Metric
            label="On-time"
            value={`${d.metrics.on_time_percent}%`}
            sub={`Accept ${d.metrics.acceptance_rate}% · Complete ${d.metrics.completion_rate}%`}
          />
        </div>

        <AiPanel ai={d.ai} />
      </div>

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
        {tab === "overview" && <OverviewTab d={d} onGoto={setTab} />}
        {tab === "identity" && <IdentityTab d={d} />}
        {tab === "documents" && <DocumentsTab id={id} />}
        {tab === "vehicles" && <VehiclesTab id={id} />}
        {tab === "orders" && <OrdersTab id={id} />}
        {tab === "performance" && <PerformanceTab d={d} />}
        {tab === "wallet" && <WalletTab id={id} />}
        {tab === "incidents" && <IncidentsTab id={id} />}
        {tab === "activities" && <ActivityTimeline entityType="driver" entityId={id} />}
        {tab === "tasks" && <EntityTasks entityType="driver" entityId={id} />}
        {tab === "timeline" && <TimelineTab id={id} />}
        {tab === "analytics" && <AnalyticsTab id={id} />}
        {tab === "settings" && <SettingsTab d={d} onChanged={refresh} />}
      </div>
    </div>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-primary/10 p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-xl font-bold text-primary">{value}</p>
      {sub && <p className="text-xs text-muted">{sub}</p>}
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

function AiPanel({ ai }: { ai: DriverDetail["ai"] }) {
  return (
    <div className="mt-4 rounded-xl border border-secondary/20 bg-secondary/5 p-4">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
        <Sparkles className="h-4 w-4 text-secondary" /> AI insights
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge tone={RISK_TONE[ai.fraud_risk]}>Fraud: {titleCase(ai.fraud_risk)}</Badge>
        <Badge tone={RISK_TONE[ai.burnout_risk]}>Burnout: {titleCase(ai.burnout_risk)}</Badge>
        <Badge tone={RISK_TONE[ai.late_delivery_risk]}>
          Late risk: {titleCase(ai.late_delivery_risk)}
        </Badge>
        <Badge tone={RISK_TONE[ai.maintenance_risk]}>
          Maintenance: {titleCase(ai.maintenance_risk)}
        </Badge>
        <Badge tone={RISK_TONE[ai.payout_anomaly]}>Payout: {titleCase(ai.payout_anomaly)}</Badge>
      </div>
      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-muted">
        Recommended training
      </p>
      <div className="mt-1 flex flex-wrap gap-1">
        {ai.recommended_training.map((t, i) => (
          <Badge key={i} tone="violet">
            {t}
          </Badge>
        ))}
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

function OverviewTab({ d, onGoto }: { d: DriverDetail; onGoto: (t: TabId) => void }) {
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <SectionCard title="Driver summary" className="lg:col-span-2">
        <dl className="grid grid-cols-2 gap-4 p-5 md:grid-cols-3">
          <Detail label="Email" value={d.email} />
          <Detail label="Phone" value={d.phone} />
          <Detail label="License class" value={d.license_class} />
          <Detail label="Service area" value={d.service_area} />
          <Detail label="Revenue (today)" value={money(d.metrics.revenue_today_cents)} />
          <Detail label="Revenue (week)" value={money(d.metrics.revenue_week_cents)} />
          <Detail label="Revenue (month)" value={money(d.metrics.revenue_month_cents)} />
          <Detail label="Cancellation rate" value={`${d.metrics.cancellation_rate}%`} />
          <Detail label="Lifetime orders" value={String(d.metrics.lifetime_orders)} />
        </dl>
      </SectionCard>
      <SectionCard title="At a glance">
        <div className="space-y-3 p-5 text-sm">
          <QuickRow
            label="Vehicles"
            value={String(d.counts.vehicles ?? 0)}
            onClick={() => onGoto("vehicles")}
          />
          <QuickRow
            label="Open incidents"
            value={String(d.counts.incidents ?? 0)}
            onClick={() => onGoto("incidents")}
          />
          <QuickRow
            label="Payouts"
            value={String(d.counts.payouts ?? 0)}
            onClick={() => onGoto("wallet")}
          />
          <QuickRow
            label="Open tasks"
            value={String(d.counts.open_tasks ?? 0)}
            onClick={() => onGoto("tasks")}
          />
          <QuickRow
            label="Background check"
            value={titleCase(d.background_check_status)}
            onClick={() => onGoto("settings")}
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

function IdentityTab({ d }: { d: DriverDetail }) {
  const raw = d.documents as Record<string, unknown>;
  const addr = (raw.address as Record<string, string>) ?? {};
  const emergency = (raw.emergency_contact as Record<string, string>) ?? {};
  return (
    <SectionCard title="Identity & personal information">
      <dl className="grid grid-cols-2 gap-4 p-5 md:grid-cols-3">
        <Detail label="Full name" value={d.full_name} />
        <Detail label="Email" value={d.email} />
        <Detail label="Phone" value={d.phone} />
        <Detail
          label="Address"
          value={
            [addr.street, addr.city, addr.province, addr.postal_code].filter(Boolean).join(", ") ||
            null
          }
        />
        <Detail label="Employment type" value={raw.employment_type as string} />
        <Detail
          label="Languages"
          value={
            Array.isArray(raw.languages)
              ? (raw.languages as string[]).join(", ")
              : (raw.languages as string)
          }
        />
        <Detail label="Emergency contact" value={emergency.name} />
        <Detail label="Emergency phone" value={emergency.phone} />
        <Detail
          label="Tax / SIN on file"
          value={raw.sin ? "Provided" : raw.tax_id ? "Provided" : null}
        />
      </dl>
    </SectionCard>
  );
}

function DocumentsTab({ id }: { id: string }) {
  const { data } = useApiData((t) => drivers.documents(t, id), [id]);
  if (!data) return <Spinner />;
  const v = data.verification;
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title="Verification">
        <div className="space-y-2 p-5">
          <VerifyRow label="Driver license" ok={v.license_verified} />
          <VerifyRow label="Insurance" ok={v.insurance_verified} />
          <VerifyRow label="Vehicle ownership / registration" ok={v.vehicle_verified} />
          <div className="flex items-center justify-between py-1.5">
            <span className="text-sm text-primary">Background check</span>
            <Badge tone={v.background_check_status === "passed" ? "green" : "amber"}>
              {titleCase(v.background_check_status)}
            </Badge>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Expiry reminders">
        <div className="divide-y divide-primary/5">
          {data.expiries.map((e, i) => {
            // eslint-disable-next-line react-hooks/purity -- relative "expiring soon" check needs the current time at render
            const soon = new Date(e.expires_at) <= new Date(Date.now() + 30 * 86400000);
            return (
              <div key={i} className="flex items-center justify-between px-5 py-3">
                <span className="text-sm text-primary">{e.label}</span>
                <Badge tone={soon ? "red" : "slate"}>{shortDate(e.expires_at)}</Badge>
              </div>
            );
          })}
          {data.expiries.length === 0 && (
            <p className="px-5 py-8 text-center text-sm text-muted">No tracked expiries.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function VerifyRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-primary">{label}</span>
      <Badge tone={ok ? "green" : "amber"}>{ok ? "Verified" : "Pending"}</Badge>
    </div>
  );
}

function VehiclesTab({ id }: { id: string }) {
  const { data } = useApiData((t) => drivers.vehicles(t, id), [id]);
  return (
    <SectionCard title={`Vehicles (${data?.length ?? 0})`}>
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((v) => (
          <div key={v.id} className="flex items-center justify-between px-5 py-3">
            <div>
              <p className="text-sm font-medium text-primary">
                {v.make_model ?? titleCase(v.vehicle_class)}{" "}
                {v.is_active && <Badge tone="green">Active</Badge>}
              </p>
              <p className="text-xs text-muted">
                {titleCase(v.vehicle_class)} · {v.plate_number} ·{" "}
                {v.capacity_kg ? `${v.capacity_kg} kg` : "—"}
              </p>
            </div>
            {v.compliance_expires_at && (
              <Badge tone="slate">Expires {shortDate(v.compliance_expires_at)}</Badge>
            )}
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">No vehicles registered.</p>
        )}
      </div>
    </SectionCard>
  );
}

function OrdersTab({ id }: { id: string }) {
  const { data } = useApiData((t) => drivers.orders(t, id), [id]);
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
          <p className="px-5 py-10 text-center text-sm text-muted">No orders assigned yet.</p>
        )}
      </div>
    </SectionCard>
  );
}

function PerformanceTab({ d }: { d: DriverDetail }) {
  const m = d.metrics;
  const bars = [
    { label: "Acceptance rate", value: m.acceptance_rate },
    { label: "Completion rate", value: m.completion_rate },
    { label: "On-time %", value: m.on_time_percent },
  ];
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <SectionCard title="Performance">
        <div className="space-y-4 p-5">
          {bars.map((b) => (
            <div key={b.label}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="text-primary">{b.label}</span>
                <span className="font-semibold text-primary">{b.value}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-gray-bg">
                <div
                  className="h-full rounded-full bg-secondary"
                  style={{ width: `${Math.min(100, b.value)}%` }}
                />
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between pt-2 text-sm">
            <span className="text-muted">Cancellation rate</span>
            <span className="font-semibold text-red-600">{m.cancellation_rate}%</span>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Ratings & quality">
        <dl className="grid grid-cols-2 gap-4 p-5">
          <Detail
            label="Customer rating"
            value={d.rating != null ? `${d.rating.toFixed(1)} / 5` : null}
          />
          <Detail label="Lifetime orders" value={String(m.lifetime_orders)} />
          <Detail label="Lifetime completed" value={String(m.lifetime_completed)} />
          <Detail label="Open incidents" value={String(m.incidents)} />
        </dl>
      </SectionCard>
    </div>
  );
}

function WalletTab({ id }: { id: string }) {
  const { data } = useApiData((t) => drivers.payouts(t, id), [id]);
  if (!data) return <Spinner />;
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Wallet balance" value={money(data.wallet_balance_cents)} />
        <Metric label="Pending payouts" value={money(data.pending_cents)} />
        <Metric label="Paid out" value={money(data.paid_cents)} />
      </div>
      <SectionCard title="Payout history">
        <div className="divide-y divide-primary/5">
          {data.payouts.map((p) => (
            <div key={p.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="text-sm font-medium text-primary">
                  {money(p.amount_cents)}{" "}
                  <span className="text-xs uppercase text-muted">{p.currency}</span>
                </p>
                <p className="text-xs text-muted">
                  {p.reference ?? "—"} · {shortDate(p.created_at)}
                </p>
              </div>
              <Badge tone={p.status === "paid" ? "green" : "amber"}>{titleCase(p.status)}</Badge>
            </div>
          ))}
          {data.payouts.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-muted">No payouts yet.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function IncidentsTab({ id }: { id: string }) {
  const { data } = useApiData((t) => drivers.incidents(t, id), [id]);
  if (!data) return <Spinner />;
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title={`Incidents (${data.incidents.length})`}>
        <div className="divide-y divide-primary/5">
          {data.incidents.map((i) => (
            <div key={i.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="text-sm font-medium text-primary">{titleCase(i.type)}</p>
                <p className="text-xs text-muted">{shortDate(i.created_at)}</p>
              </div>
              <Badge tone={i.status === "resolved" ? "green" : "amber"}>
                {titleCase(i.status)}
              </Badge>
            </div>
          ))}
          {data.incidents.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-muted">No incidents on record.</p>
          )}
        </div>
      </SectionCard>
      <SectionCard title={`Claims (${data.claims.length})`}>
        <div className="divide-y divide-primary/5">
          {data.claims.map((c) => (
            <div key={c.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="text-sm font-medium text-primary">{titleCase(c.claim_type)}</p>
                <p className="text-xs text-muted">{shortDate(c.created_at)}</p>
              </div>
              <Badge tone={c.status === "resolved" ? "green" : "amber"}>
                {titleCase(c.status)}
              </Badge>
            </div>
          ))}
          {data.claims.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-muted">No claims.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function TimelineTab({ id }: { id: string }) {
  const { data } = useApiData((t) => drivers.timeline(t, id), [id]);
  const tone: Record<string, string> = {
    activity: "bg-secondary",
    order: "bg-violet-500",
    payout: "bg-amber-500",
  };
  return (
    <SectionCard title="Timeline">
      <div className="p-5">
        {(data ?? []).map((e, i) => (
          <div key={i} className="flex gap-3 pb-4 last:pb-0">
            <div className="flex flex-col items-center">
              <span className={cn("h-2.5 w-2.5 rounded-full", tone[e.kind] ?? "bg-slate-400")} />
              {i < (data?.length ?? 0) - 1 && <span className="w-px flex-1 bg-primary/10" />}
            </div>
            <div className="-mt-1">
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
  const { data } = useApiData((t) => drivers.analytics(t, id), [id]);
  if (!data) return <Spinner />;
  const max = Math.max(1, ...data.by_month.map((r) => r.orders));
  return (
    <SectionCard title="Orders & revenue by month">
      <div className="space-y-3 p-5">
        {data.by_month.map((r) => (
          <div key={r.month}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="text-primary">
                {r.month}{" "}
                <span className="text-muted">
                  · {r.completed}/{r.orders} completed
                </span>
              </span>
              <span className="font-semibold text-primary">{money(r.revenue_cents)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-bg">
              <div
                className="h-full rounded-full bg-secondary"
                style={{ width: `${(r.orders / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
        {data.by_month.length === 0 && (
          <p className="py-6 text-center text-sm text-muted">No order history yet.</p>
        )}
      </div>
    </SectionCard>
  );
}

function SettingsTab({ d, onChanged }: { d: DriverDetail; onChanged: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  async function verify(patch: Record<string, boolean | string>) {
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.verify(token, d.id, patch);
      onChanged();
    } finally {
      setBusy(false);
    }
  }
  async function action(type: string) {
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.action(token, d.id, { type });
      setToast(`${titleCase(type)} recorded.`);
      setTimeout(() => setToast(null), 2500);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title="Verification & compliance">
        <div className="space-y-2 p-5">
          <ToggleRow
            label="License verified"
            value={d.license_verified}
            onToggle={() => verify({ license_verified: !d.license_verified })}
            busy={busy}
          />
          <ToggleRow
            label="Insurance verified"
            value={d.insurance_verified}
            onToggle={() => verify({ insurance_verified: !d.insurance_verified })}
            busy={busy}
          />
          <ToggleRow
            label="Vehicle verified"
            value={d.vehicle_verified}
            onToggle={() => verify({ vehicle_verified: !d.vehicle_verified })}
            busy={busy}
          />
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-primary">Background check</span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="px-2 py-1 text-xs"
                onClick={() => verify({ background_check_status: "passed" })}
                disabled={busy}
              >
                Pass
              </Button>
              <Button
                variant="outline"
                className="px-2 py-1 text-xs"
                onClick={() => verify({ background_check_status: "failed" })}
                disabled={busy}
              >
                Fail
              </Button>
            </div>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Operations">
        <div className="flex flex-wrap gap-2 p-5">
          <Button variant="outline" onClick={() => action("push")} disabled={busy}>
            <Send className="h-4 w-4" /> Send push
          </Button>
          <Button variant="outline" onClick={() => action("sms")} disabled={busy}>
            <Send className="h-4 w-4" /> Send SMS
          </Button>
          <Button variant="outline" onClick={() => action("email")} disabled={busy}>
            <Mail className="h-4 w-4" /> Email driver
          </Button>
          <Button variant="outline" onClick={() => action("request_documents")} disabled={busy}>
            <FileText className="h-4 w-4" /> Request documents
          </Button>
          <Button variant="outline" onClick={() => action("reset_password")} disabled={busy}>
            <CreditCard className="h-4 w-4" /> Reset password
          </Button>
          {toast && <span className="w-full text-sm text-green-600">{toast}</span>}
        </div>
      </SectionCard>
    </div>
  );
}

function ToggleRow({
  label,
  value,
  onToggle,
  busy,
}: {
  label: string;
  value: boolean;
  onToggle: () => void;
  busy: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-primary">{label}</span>
      <button
        onClick={onToggle}
        disabled={busy}
        className={cn(
          "rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset",
          value
            ? "bg-green-50 text-green-700 ring-green-600/20"
            : "bg-amber-50 text-amber-700 ring-amber-600/20"
        )}
      >
        {value ? "Verified" : "Mark verified"}
      </button>
    </div>
  );
}
