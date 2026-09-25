"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  Activity as ActivityIcon,
  AlertTriangle,
  ArrowLeft,
  Boxes,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  FileText,
  Gauge,
  IdCard,
  Info,
  Mail,
  Package,
  ShieldCheck,
  Sparkles,
  Star,
  Truck,
  Wallet,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { useApiData } from "@/hooks/useApiData";
import { drivers, type DriverDetail } from "@/lib/drivers";
import { EntityAlertsPanel } from "@/components/alerts/EntityAlertsPanel";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { EntityTasks } from "@/components/crm/EntityTasks";
import { Badge, Button, SectionCard, Spinner } from "@/components/crm/primitives";
import { money, shortDate, titleCase, dateTime } from "@/lib/crmFormat";
import AdminPage from "@/components/layout/AdminPage";

const DocumentsTab = dynamic(
  () => import("@/components/drivers/DriverDocumentsTab").then((m) => m.DocumentsTab),
  { loading: () => <Spinner /> }
);
const VehiclesTab = dynamic(
  () => import("@/components/drivers/DriverVehiclesTab").then((m) => m.VehiclesTab),
  { loading: () => <Spinner /> }
);
const IdentityTab = dynamic(
  () => import("@/components/drivers/DriverIdentityTab").then((m) => m.IdentityTab),
  { loading: () => <Spinner /> }
);
const OrdersTab = dynamic(
  () => import("@/components/drivers/DriverOrdersTab").then((m) => m.OrdersTab),
  { loading: () => <Spinner /> }
);
const PerformanceTab = dynamic(
  () => import("@/components/drivers/DriverPerformanceTab").then((m) => m.PerformanceTab),
  { loading: () => <Spinner /> }
);
const WalletTab = dynamic(
  () => import("@/components/drivers/DriverWalletTab").then((m) => m.WalletTab),
  { loading: () => <Spinner /> }
);
const IncidentsTab = dynamic(
  () => import("@/components/drivers/DriverIncidentsTab").then((m) => m.IncidentsTab),
  { loading: () => <Spinner /> }
);
const TimelineTab = dynamic(
  () => import("@/components/drivers/DriverTimelineTab").then((m) => m.TimelineTab),
  { loading: () => <Spinner /> }
);
const AnalyticsTab = dynamic(
  () => import("@/components/drivers/DriverAnalyticsTab").then((m) => m.AnalyticsTab),
  { loading: () => <Spinner /> }
);
const SettingsTab = dynamic(
  () => import("@/components/drivers/DriverSettingsTab").then((m) => m.SettingsTab),
  { loading: () => <Spinner /> }
);

const STATUS_TONE: Record<string, string> = {
  APPROVED: "green",
  PENDING: "amber",
  SUSPENDED: "red",
  REJECTED: "slate",
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

const READ_ONLY_ROLES = new Set([
  "support",
  "support_lead",
  "sales",
  "sales_manager",
  "finance",
  "read_only",
  "developer",
  "marketing",
]);

const TAB_IDS = new Set<string>([
  "overview",
  "identity",
  "documents",
  "vehicles",
  "orders",
  "performance",
  "wallet",
  "incidents",
  "activities",
  "tasks",
  "timeline",
  "analytics",
  "settings",
]);
const PRIMARY_TAB_IDS = new Set<TabId>(["overview", "identity", "documents", "vehicles", "orders"]);
const PRIMARY_TABS = TABS.filter((t) => PRIMARY_TAB_IDS.has(t.id));
const MORE_TABS = TABS.filter((t) => !PRIMARY_TAB_IDS.has(t.id));

export default function DriverDetailClient() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = params.id;
  const { getApiToken } = useAdminAuth();
  const { profile } = useAdminProfile();
  const canWrite = !READ_ONLY_ROLES.has((profile?.role || "").toLowerCase());
  const [version, setVersion] = useState(0);
  const requested = searchParams.get("tab") || "overview";
  const tab = (TAB_IDS.has(requested) ? requested : "overview") as TabId;
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const { data: d, error } = useApiData((t) => drivers.detail(t, id), [id, version], {
    key: `driver-detail-${id}`,
  });
  const refresh = () => setVersion((v) => v + 1);

  function setTab(next: TabId) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", next);
    router.replace(`/drivers/${id}?${params.toString()}`);
  }

  async function lifecycle(action: "approve" | "suspend" | "reject" | "rehire") {
    setBusy(true);
    setActionError(null);
    try {
      const token = await getApiToken();
      if (action === "approve") {
        await drivers.approve(token, id);
      } else if (action === "reject") {
        const res = await drivers.reject(token, id, rejectReason.trim());
        setRejectOpen(false);
        setRejectReason("");
        if (res.fleetbase_sync_warning) {
          setActionError(
            "Driver rejected in PorterChain, but Fleetbase offline sync failed — verify they are not still assignable in Execution."
          );
        }
      } else if (action === "rehire") {
        await drivers.rehire(token, id);
      } else {
        const res = await drivers.deactivate(token, id);
        if (res.fleetbase_sync_warning) {
          setActionError(
            "Driver deactivated in PorterChain, but Fleetbase offline sync failed — verify they are not still assignable in Execution."
          );
        }
      }
      refresh();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : `${action} failed`);
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!d) return <Spinner label="Loading driver…" />;

  return (
    <AdminPage>
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
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold text-primary">{d.full_name}</h1>
                <Badge tone={STATUS_TONE[d.status] ?? "slate"}>{titleCase(d.status)}</Badge>
                {d.medical_transport_certified && <Badge tone="sky">Medical certified</Badge>}
                {d.fleetbase_driver_id ? (
                  <Badge tone="green">Fleetbase linked</Badge>
                ) : (
                  <Badge tone="amber">Not linked to execution</Badge>
                )}
                {d.clerk_linked === false && <Badge tone="amber">Sign-in not connected</Badge>}
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
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/settings?section=users&tab=driver"
              className="inline-flex items-center rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
            >
              Users directory
            </Link>
            {canWrite && d.clerk_linked === false && (
              <Button
                variant="outline"
                disabled={busy}
                onClick={() => {
                  setBusy(true);
                  setActionError(null);
                  void getApiToken()
                    .then((token) => drivers.invite(token, id))
                    .then(() => refresh())
                    .catch((e) => setActionError(e instanceof Error ? e.message : "Invite failed"))
                    .finally(() => setBusy(false));
                }}
              >
                <Mail className="h-4 w-4" /> Resend invite
              </Button>
            )}
            {canWrite && d.status !== "APPROVED" && d.status !== "REJECTED" && (
              <Button onClick={() => lifecycle("approve")} disabled={busy}>
                <CheckCircle2 className="h-4 w-4" /> Approve
              </Button>
            )}
            {canWrite && (d.status === "REJECTED" || d.status === "SUSPENDED") && (
              <Button onClick={() => lifecycle("rehire")} disabled={busy}>
                Rehire
              </Button>
            )}
            {canWrite && d.status !== "SUSPENDED" && d.status !== "REJECTED" && (
              <Button variant="outline" onClick={() => lifecycle("suspend")} disabled={busy}>
                Deactivate
              </Button>
            )}
            {canWrite && d.status !== "REJECTED" && (
              <Button variant="outline" onClick={() => setRejectOpen(true)} disabled={busy}>
                Reject
              </Button>
            )}
          </div>
        </div>
        {rejectOpen && (
          <form
            className="mt-3 flex flex-wrap items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (!rejectReason.trim()) {
                setActionError("A reason is required to reject this driver.");
                return;
              }
              void lifecycle("reject");
            }}
          >
            <label className="min-w-[16rem] flex-1 text-sm">
              <span className="text-xs text-muted">Reason for rejecting this driver</span>
              <input
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                placeholder="Tell the driver why"
              />
            </label>
            <Button type="submit" disabled={busy}>
              Confirm reject
            </Button>
            <Button type="button" variant="outline" onClick={() => setRejectOpen(false)}>
              Cancel
            </Button>
          </form>
        )}
        {(d.assign_blockers?.length ?? 0) > 0 && (
          <p className="mt-3 text-sm text-amber-800">
            Dispatch will not assign this driver. {d.assign_blockers?.join(" ")}
          </p>
        )}
        {!d.fleetbase_driver_id && (
          <p className="mt-2 text-sm text-muted">
            Not linked to execution — assigned jobs will not show on Orders until Fleetbase has this
            driver.
          </p>
        )}
        {actionError && (
          <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {actionError}
          </p>
        )}

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

      <div className="sticky top-0 z-30 flex items-center gap-1 rounded-2xl border border-primary/10 bg-white/95 p-1.5 backdrop-blur">
        <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
          {PRIMARY_TABS.map(({ id: tid, label, icon: Icon }) => (
            <button
              key={tid}
              type="button"
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
        <details className="relative shrink-0">
          <summary
            className={cn(
              "flex cursor-pointer list-none items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium",
              MORE_TABS.some((t) => t.id === tab)
                ? "bg-secondary text-white"
                : "text-primary/70 hover:bg-gray-bg"
            )}
          >
            {MORE_TABS.find((t) => t.id === tab)?.label ?? "More"}
            <ChevronDown className="h-3.5 w-3.5 opacity-70" />
          </summary>
          <div className="absolute right-0 z-40 mt-1 min-w-[12rem] rounded-xl border border-primary/10 bg-white p-1 shadow-lg">
            {MORE_TABS.map(({ id: tid, label, icon: Icon }) => (
              <button
                key={tid}
                type="button"
                onClick={(e) => {
                  setTab(tid);
                  e.currentTarget.closest("details")?.removeAttribute("open");
                }}
                className={cn(
                  "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm",
                  tab === tid
                    ? "bg-secondary/10 font-medium text-secondary"
                    : "text-primary hover:bg-gray-bg"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
        </details>
      </div>

      <div>
        {tab === "overview" && <OverviewTab d={d} onGoto={setTab} />}
        {tab === "identity" && <IdentityTab d={d} canWrite={canWrite} onChanged={refresh} />}
        {tab === "documents" && (
          <DocumentsTab id={id} driver={d} canWrite={canWrite} onChanged={refresh} />
        )}
        {tab === "vehicles" && <VehiclesTab id={id} canWrite={canWrite} />}
        {tab === "orders" && <OrdersTab id={id} blockers={d.assign_blockers ?? []} />}
        {tab === "performance" && <PerformanceTab d={d} />}
        {tab === "wallet" && <WalletTab id={id} />}
        {tab === "incidents" && <IncidentsTab id={id} />}
        {tab === "activities" && <ActivityTimeline entityType="driver" entityId={id} />}
        {tab === "tasks" && <EntityTasks entityType="driver" entityId={id} />}
        {tab === "timeline" && <TimelineTab id={id} />}
        {tab === "analytics" && <AnalyticsTab id={id} />}
        {tab === "settings" && <SettingsTab d={d} canWrite={canWrite} onChanged={refresh} />}
      </div>
    </AdminPage>
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
    <div className="space-y-5">
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
              label="Documents"
              value={d.docs_pending_review ? "Needs review" : "Open"}
              onClick={() => onGoto("documents")}
            />
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
              onClick={() => onGoto("documents")}
            />
          </div>
        </SectionCard>
      </div>
      <EntityAlertsPanel
        recipientType="driver"
        recipientId={d.id}
        showDevices
        careHref={`/drivers/${d.id}?tab=incidents`}
      />
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
