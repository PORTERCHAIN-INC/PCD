"use client";

import { useState } from "react";
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
  Send,
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
import { AddDriverDocumentForm } from "@/components/drivers/AddDriverDocumentForm";
import { EntityAlertsPanel } from "@/components/alerts/EntityAlertsPanel";
import { ListPager } from "@/components/crm/ListPager";
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

export default function DriverDetailPage() {
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

function IdentityTab({
  d,
  canWrite,
  onChanged,
}: {
  d: DriverDetail;
  canWrite: boolean;
  onChanged: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const raw = d.documents as Record<string, unknown>;
  const addr = (raw.address as Record<string, string>) ?? {};
  const emergency = (raw.emergency_contact as Record<string, string>) ?? {};
  const [editing, setEditing] = useState(false);
  const [fullName, setFullName] = useState(d.full_name);
  const [phone, setPhone] = useState(d.phone || "");
  const [licenseClass, setLicenseClass] = useState(d.license_class || "");
  const [serviceArea, setServiceArea] = useState(d.service_area || "");
  const [street, setStreet] = useState(addr.street || "");
  const [city, setCity] = useState(addr.city || "");
  const [province, setProvince] = useState(addr.province || "");
  const [postal, setPostal] = useState(addr.postal_code || "");
  const [emergencyName, setEmergencyName] = useState(emergency.name || "");
  const [emergencyPhone, setEmergencyPhone] = useState(emergency.phone || "");
  const [error, setError] = useState<string | null>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const token = await getApiToken();
      await drivers.updateProfile(token, d.id, {
        full_name: fullName,
        phone,
        license_class: licenseClass,
        service_area: serviceArea,
        address: { street, city, province, postal_code: postal },
        emergency_contact: { name: emergencyName, phone: emergencyPhone },
      });
      setEditing(false);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save identity");
    }
  }

  return (
    <SectionCard
      title="Identity & personal information"
      action={
        canWrite ? (
          <Button variant="outline" onClick={() => setEditing((v) => !v)}>
            {editing ? "Close" : "Edit"}
          </Button>
        ) : undefined
      }
    >
      {editing ? (
        <form onSubmit={save} className="grid gap-3 p-5 sm:grid-cols-2">
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Full name"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Phone"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={licenseClass}
            onChange={(e) => setLicenseClass(e.target.value)}
            placeholder="License class"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={serviceArea}
            onChange={(e) => setServiceArea(e.target.value)}
            placeholder="Service area"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm sm:col-span-2"
            value={street}
            onChange={(e) => setStreet(e.target.value)}
            placeholder="Street"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="City"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={province}
            onChange={(e) => setProvince(e.target.value)}
            placeholder="Province"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={postal}
            onChange={(e) => setPostal(e.target.value)}
            placeholder="Postal code"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={emergencyName}
            onChange={(e) => setEmergencyName(e.target.value)}
            placeholder="Emergency contact"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={emergencyPhone}
            onChange={(e) => setEmergencyPhone(e.target.value)}
            placeholder="Emergency phone"
          />
          {error && <p className="text-sm text-red-600 sm:col-span-2">{error}</p>}
          <Button type="submit">Save identity</Button>
        </form>
      ) : (
        <dl className="grid grid-cols-2 gap-4 p-5 md:grid-cols-3">
          <Detail label="Full name" value={d.full_name} />
          <Detail label="Email" value={d.email} />
          <Detail label="Phone" value={d.phone} />
          <Detail
            label="Address"
            value={
              [addr.street, addr.city, addr.province, addr.postal_code]
                .filter(Boolean)
                .join(", ") || null
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
          <Detail label="Fleetbase driver id" value={d.fleetbase_driver_id} />
        </dl>
      )}
    </SectionCard>
  );
}

function DocumentsTab({
  id,
  driver,
  canWrite,
  onChanged,
}: {
  id: string;
  driver: DriverDetail;
  canWrite: boolean;
  onChanged: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [docVersion, setDocVersion] = useState(0);
  const [reasonFor, setReasonFor] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [docError, setDocError] = useState<string | null>(null);
  const { data, error } = useApiData((t) => drivers.documents(t, id), [id, docVersion], {
    key: `driver-documents-${id}`,
  });
  if (!data && !error) return <Spinner />;
  const v = data?.verification ?? {
    license_verified: driver.license_verified,
    insurance_verified: driver.insurance_verified,
    vehicle_verified: driver.vehicle_verified,
    background_check_status: driver.background_check_status,
  };
  const files = data?.files ?? [];
  const expiries = data?.expiries ?? [];
  const refreshDocs = () => {
    setDocVersion((n) => n + 1);
    onChanged();
  };
  async function decide(docType: string, decision: "verified" | "rejected", why?: string) {
    setDocError(null);
    try {
      const token = await getApiToken();
      await drivers.decideDocument(token, id, { doc_type: docType, decision, reason: why });
      setReasonFor(null);
      setReason("");
      refreshDocs();
    } catch (err) {
      setDocError(err instanceof Error ? err.message : "Could not update document");
    }
  }
  const attestTypes = [
    { type: "license", label: "License" },
    { type: "insurance", label: "Insurance" },
    { type: "vehicle_registration", label: "Vehicle" },
    { type: "background_check", label: "Background check" },
  ];
  return (
    <div className="space-y-5">
      {error && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          Could not load document metadata: {error}. Showing verification from driver profile.
        </p>
      )}
      {docError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {docError}
        </p>
      )}
      {canWrite && (
        <SectionCard title="Verify without a file">
          <div className="flex flex-wrap gap-2 p-5">
            {attestTypes.map((item) => (
              <Button
                key={item.type}
                variant="outline"
                onClick={() => void decide(item.type, "verified")}
              >
                Verify {item.label}
              </Button>
            ))}
          </div>
        </SectionCard>
      )}
      <div className="grid gap-5 md:grid-cols-2">
        <SectionCard title="Verification">
          <div className="space-y-2 p-5">
            <VerifyRow
              label="Driver license"
              ok={v.license_verified}
              source={data?.sources?.license}
            />
            <VerifyRow
              label="Insurance"
              ok={v.insurance_verified}
              source={data?.sources?.insurance}
            />
            <VerifyRow
              label="Vehicle ownership / registration"
              ok={v.vehicle_verified}
              source={data?.sources?.vehicle_registration}
            />
            <VerifyRow
              label="Background check"
              ok={["passed", "cleared", "approved"].includes(
                (v.background_check_status || "").toLowerCase()
              )}
              source={data?.sources?.background_check}
              statusLabel={titleCase(v.background_check_status || "pending")}
            />
            <VerifyRow
              label="Ontario abstract"
              ok={Boolean(v.abstract_verified ?? data?.sources?.abstract?.verified)}
              source={data?.sources?.abstract}
            />
            {(v.score != null || v.quality_bonus != null) && (
              <p className="pt-2 text-xs text-muted">
                Completeness {v.score ?? 0}/4
                {v.quality_bonus ? ` · Auto quality +${v.quality_bonus}` : ""}
              </p>
            )}
          </div>
        </SectionCard>
        <SectionCard title="Expiry reminders">
          <div className="divide-y divide-primary/5">
            {expiries.map((e, i) => {
              // eslint-disable-next-line react-hooks/purity -- relative "expiring soon" check needs the current time at render
              const soon = new Date(e.expires_at) <= new Date(Date.now() + 30 * 86400000);
              return (
                <div key={i} className="flex items-center justify-between px-5 py-3">
                  <span className="text-sm text-primary">{e.label}</span>
                  <Badge tone={soon ? "red" : "slate"}>{shortDate(e.expires_at)}</Badge>
                </div>
              );
            })}
            {expiries.length === 0 && (
              <p className="px-5 py-8 text-center text-sm text-muted">No tracked expiries.</p>
            )}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title={`Uploaded documents (${files.length})`}
        action={<AddDriverDocumentForm driverId={id} onAdded={refreshDocs} />}
      >
        <div className="divide-y divide-primary/5">
          {files.map((file, i) => {
            const f = file as Record<string, string | boolean | null | undefined>;
            const label = (f.label as string) || titleCase(String(f.doc_type ?? "document"));
            const href = f.file_url ? String(f.file_url) : "";
            const isDataImage = href.startsWith("data:image");
            const isHttp = href.startsWith("http://") || href.startsWith("https://");
            const status = String(f.status ?? (f.verified ? "verified" : ""));
            return (
              <div
                key={String(f.id ?? i)}
                className="flex flex-wrap items-start justify-between gap-3 px-5 py-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-primary">{label}</p>
                  <p className="text-xs text-muted">
                    {titleCase(String(f.doc_type ?? ""))}
                    {f.reference_number ? ` · Ref ${f.reference_number}` : ""}
                  </p>
                  {f.notes ? <p className="mt-1 text-xs text-muted">{String(f.notes)}</p> : null}
                  {status === "rejected" && f.rejection_reason ? (
                    <p className="mt-1 text-xs text-red-700">{String(f.rejection_reason)}</p>
                  ) : null}
                  {isDataImage ? (
                    // Mobile uploads are stored as data URLs. A normal link cannot open them.
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={href}
                      alt={label}
                      className="mt-2 max-h-48 max-w-full rounded-lg border border-primary/10 object-contain"
                    />
                  ) : null}
                </div>
                <div className="flex flex-col items-end gap-1 text-xs">
                  {(() => {
                    const portalKey = String(f.doc_type ?? "")
                      .toLowerCase()
                      .replace("driver_license", "license")
                      .replace("drivers_license", "license")
                      .replace("vehicle_reg", "vehicle_registration")
                      .replace("mto_abstract", "abstract")
                      .replace("driver_abstract", "abstract");
                    const src =
                      data?.sources?.[portalKey] || data?.sources?.[String(f.doc_type ?? "")];
                    const sourceLabel = src?.source;
                    if (!sourceLabel || sourceLabel === "unknown") return null;
                    return (
                      <Badge tone={sourceLabel === "manual" ? "slate" : "green"}>
                        {sourceLabel === "rules"
                          ? "Rules"
                          : sourceLabel === "auto"
                            ? "Auto"
                            : "Manual"}
                        {src?.provider ? ` · ${String(src.provider).replace(/_/g, " ")}` : ""}
                      </Badge>
                    );
                  })()}
                  {status ? (
                    <Badge tone={status === "verified" || f.verified ? "green" : "amber"}>
                      {titleCase(status.replace(/_/g, " "))}
                    </Badge>
                  ) : null}
                  {f.expires_at && (
                    <Badge tone="slate">Expires {shortDate(String(f.expires_at))}</Badge>
                  )}
                  {isHttp ? (
                    <a
                      href={href}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium text-secondary hover:underline"
                    >
                      View file
                    </a>
                  ) : null}
                  {canWrite &&
                    [
                      "license",
                      "driver_license",
                      "drivers_license",
                      "insurance",
                      "insurance_certificate",
                      "vehicle_registration",
                      "vehicle_reg",
                      "registration",
                      "background_check",
                      "abstract",
                      "driver_abstract",
                      "mto_abstract",
                    ].includes(String(f.doc_type ?? "").toLowerCase()) && (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="font-medium text-secondary hover:underline"
                          onClick={() => void decide(String(f.doc_type ?? ""), "verified")}
                        >
                          Verify
                        </button>
                        <button
                          type="button"
                          className="font-medium text-red-700 hover:underline"
                          onClick={() => {
                            setReasonFor(String(f.doc_type ?? ""));
                            setReason("");
                          }}
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  {reasonFor === String(f.doc_type ?? "") && (
                    <form
                      className="mt-1 flex gap-1"
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (!reason.trim()) return;
                        void decide(String(f.doc_type ?? ""), "rejected", reason.trim());
                      }}
                    >
                      <input
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder="Reason"
                        className="rounded-lg border border-primary/15 px-2 py-1 text-xs"
                      />
                      <button type="submit" className="text-xs font-medium text-red-700">
                        Send
                      </button>
                    </form>
                  )}
                  {f.uploaded_at && (
                    <span className="text-muted">Added {shortDate(String(f.uploaded_at))}</span>
                  )}
                </div>
              </div>
            );
          })}
          {files.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-muted">
              No documents on file yet. Use Add document to attach license, insurance, or compliance
              records.
            </p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function VerifyRow({
  label,
  ok,
  source,
  statusLabel,
}: {
  label: string;
  ok: boolean;
  source?: {
    source: string;
    provider?: string | null;
  };
  statusLabel?: string;
}) {
  const sourceTone =
    source?.source === "auto" || source?.source === "rules"
      ? "green"
      : source?.source === "manual"
        ? "slate"
        : "amber";
  const sourceText =
    source?.source === "auto"
      ? "Auto"
      : source?.source === "rules"
        ? "Rules"
        : source?.source === "manual"
          ? "Manual"
          : null;
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-sm text-primary">{label}</span>
      <div className="flex flex-wrap items-center justify-end gap-1">
        {sourceText && ok && (
          <Badge tone={sourceTone}>
            {sourceText}
            {source?.provider ? ` · ${String(source.provider).replace(/_/g, " ")}` : ""}
          </Badge>
        )}
        <Badge tone={ok ? "green" : "amber"}>{statusLabel ?? (ok ? "Verified" : "Pending")}</Badge>
      </div>
    </div>
  );
}

function VehiclesTab({ id, canWrite }: { id: string; canWrite: boolean }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const [open, setOpen] = useState(false);
  const [vehicleClass, setVehicleClass] = useState("cargoVan");
  const [plate, setPlate] = useState("");
  const [makeModel, setMakeModel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editClass, setEditClass] = useState("cargoVan");
  const [editPlate, setEditPlate] = useState("");
  const [editMake, setEditMake] = useState("");
  const vehicleClasses = ["sedan", "suv", "pickup", "cargoVan", "highRoof", "box16", "box20"];
  const classOptions = (current: string) =>
    vehicleClasses.includes(current) ? vehicleClasses : [current, ...vehicleClasses];
  const { data } = useApiData((t) => drivers.vehicles(t, id), [id, version], {
    key: `driver-vehicles-${id}`,
  });
  async function addVehicle(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const token = await getApiToken();
      await drivers.addVehicle(token, id, {
        vehicle_class: vehicleClass,
        plate_number: plate,
        make_model: makeModel || undefined,
      });
      setPlate("");
      setMakeModel("");
      setOpen(false);
      setVersion((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add vehicle");
    }
  }
  async function setActive(vehicleId: string, active: boolean) {
    setError(null);
    try {
      const token = await getApiToken();
      if (active) await drivers.updateVehicle(token, id, vehicleId, { is_active: true });
      else await drivers.deactivateVehicle(token, id, vehicleId);
      setVersion((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update vehicle");
    }
  }
  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editingId) return;
    setError(null);
    try {
      const token = await getApiToken();
      await drivers.updateVehicle(token, id, editingId, {
        vehicle_class: editClass,
        plate_number: editPlate,
        make_model: editMake || undefined,
      });
      setEditingId(null);
      setVersion((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update vehicle");
    }
  }
  return (
    <SectionCard
      title={`Vehicles (${data?.length ?? 0})`}
      action={
        canWrite ? (
          <Button variant="outline" onClick={() => setOpen((v) => !v)}>
            Add vehicle
          </Button>
        ) : undefined
      }
    >
      {open && (
        <form
          onSubmit={addVehicle}
          className="grid gap-2 border-b border-primary/10 p-5 sm:grid-cols-3"
        >
          <select
            value={vehicleClass}
            onChange={(e) => setVehicleClass(e.target.value)}
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
          >
            {classOptions(vehicleClass).map((item) => (
              <option key={item} value={item}>
                {titleCase(item)}
              </option>
            ))}
          </select>
          <input
            value={plate}
            onChange={(e) => setPlate(e.target.value)}
            placeholder="Plate"
            required
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
          />
          <input
            value={makeModel}
            onChange={(e) => setMakeModel(e.target.value)}
            placeholder="Make and model"
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
          />
          <Button type="submit">Save vehicle</Button>
          {error && <p className="text-sm text-red-600 sm:col-span-3">{error}</p>}
        </form>
      )}
      {error && <p className="px-5 pt-3 text-sm text-red-600">{error}</p>}
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((v) => (
          <div key={v.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
            {editingId === v.id ? (
              <form onSubmit={saveEdit} className="grid w-full gap-2 sm:grid-cols-4">
                <select
                  value={editClass}
                  onChange={(e) => setEditClass(e.target.value)}
                  className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
                >
                  {classOptions(editClass).map((item) => (
                    <option key={item} value={item}>
                      {titleCase(item)}
                    </option>
                  ))}
                </select>
                <input
                  value={editPlate}
                  onChange={(e) => setEditPlate(e.target.value)}
                  required
                  className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
                />
                <input
                  value={editMake}
                  onChange={(e) => setEditMake(e.target.value)}
                  placeholder="Make and model"
                  className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
                />
                <div className="flex gap-2">
                  <Button type="submit">Save</Button>
                  <Button type="button" variant="outline" onClick={() => setEditingId(null)}>
                    Cancel
                  </Button>
                </div>
              </form>
            ) : (
              <>
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
                <div className="flex items-center gap-2">
                  {v.compliance_expires_at && (
                    <Badge tone="slate">Expires {shortDate(v.compliance_expires_at)}</Badge>
                  )}
                  {canWrite && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        setEditingId(v.id);
                        setEditClass(v.vehicle_class);
                        setEditPlate(v.plate_number);
                        setEditMake(v.make_model ?? "");
                      }}
                    >
                      Edit
                    </Button>
                  )}
                  {canWrite && v.is_active && (
                    <Button variant="outline" onClick={() => void setActive(v.id, false)}>
                      Take off the road
                    </Button>
                  )}
                  {canWrite && !v.is_active && (
                    <Button variant="outline" onClick={() => void setActive(v.id, true)}>
                      Set active
                    </Button>
                  )}
                </div>
              </>
            )}
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            No vehicles yet. {canWrite ? "Add the vehicle this driver will use." : ""}
          </p>
        )}
      </div>
    </SectionCard>
  );
}

function OrdersTab({ id, blockers }: { id: string; blockers: string[] }) {
  const [offset, setOffset] = useState(0);
  const { data } = useApiData((t) => drivers.orders(t, id, { limit: 50, offset }), [id, offset], {
    key: `driver-orders-${id}-${offset}`,
  });
  const items = data?.items ?? [];
  return (
    <SectionCard title={`Orders (${data?.total ?? 0})`}>
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
            {items.map((o) => (
              <tr key={o.id} className="border-b border-primary/5">
                <td className="px-4 py-2 font-medium text-primary">
                  <Link href={`/orders/${o.id}`} className="text-secondary hover:underline">
                    {o.order_number}
                  </Link>
                </td>
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
        {items.length === 0 && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            No orders are assigned to this driver. Assign from the order.
            {blockers.length > 0 ? ` ${blockers.join(" ")}` : ""}
          </p>
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
  const { getApiToken } = useAdminAuth();
  const { data, error, refetch } = useApiData((t) => drivers.payouts(t, id), [id], {
    key: `driver-payouts-${id}`,
  });
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  if (!data && !error) return <Spinner />;
  const payouts = data?.payouts ?? [];
  const wallet = data?.wallet_balance_cents ?? 0;

  async function createPayout() {
    if (wallet <= 0) {
      setToast("Wallet has no balance to cash out.");
      setTimeout(() => setToast(null), 2500);
      return;
    }
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.createPayout(token, id);
      await refetch();
      setToast("Pending payout created from wallet.");
      setTimeout(() => setToast(null), 2500);
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Payout failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }

  async function markPaid(payoutId: string) {
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.markPayoutPaid(token, id, payoutId);
      await refetch();
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Mark paid failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Wallet balance" value={money(wallet)} />
        <Metric label="Pending payouts" value={money(data?.pending_cents ?? 0)} />
        <Metric label="Paid out" value={money(data?.paid_cents ?? 0)} />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={createPayout} disabled={busy || wallet <= 0}>
          <Wallet className="h-4 w-4" /> Create payout from wallet
        </Button>
        {toast && <span className="text-sm text-muted">{toast}</span>}
      </div>
      <SectionCard title="Payout history">
        <div className="divide-y divide-primary/5">
          {payouts.map((p) => (
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
              <div className="flex items-center gap-2">
                <Badge tone={p.status === "paid" ? "green" : "amber"}>{titleCase(p.status)}</Badge>
                {p.status === "pending" && (
                  <Button
                    variant="outline"
                    className="px-2 py-1 text-xs"
                    disabled={busy}
                    onClick={() => markPaid(p.id)}
                  >
                    Mark paid
                  </Button>
                )}
              </div>
            </div>
          ))}
          {payouts.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-muted">
              No payouts yet — earnings stay in wallet until you create a cash-out.
            </p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function IncidentsTab({ id }: { id: string }) {
  const { data, error } = useApiData((t) => drivers.incidents(t, id), [id], {
    key: `driver-incidents-${id}`,
  });
  if (!data && !error) return <Spinner />;
  const incidents = data?.incidents ?? [];
  const claims = data?.claims ?? [];
  return (
    <div className="space-y-5">
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="grid gap-5 md:grid-cols-2">
        <SectionCard title={`Incidents (${incidents.length})`}>
          <div className="divide-y divide-primary/5">
            {incidents.map((i) => (
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
            {incidents.length === 0 && (
              <p className="px-5 py-10 text-center text-sm text-muted">No incidents on record.</p>
            )}
          </div>
        </SectionCard>
        <SectionCard title={`Claims (${claims.length})`}>
          <div className="divide-y divide-primary/5">
            {claims.map((c) => (
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
            {claims.length === 0 && (
              <p className="px-5 py-10 text-center text-sm text-muted">No claims.</p>
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}

function TimelineTab({ id }: { id: string }) {
  const { data } = useApiData((t) => drivers.timeline(t, id), [id], {
    key: `driver-timeline-${id}`,
  });
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
  const { data } = useApiData((t) => drivers.analytics(t, id), [id], {
    key: `driver-analytics-${id}`,
  });
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

function SettingsTab({
  d,
  canWrite,
  onChanged,
}: {
  d: DriverDetail;
  canWrite: boolean;
  onChanged: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  async function decide(
    docType: string,
    decision: "verified" | "rejected" | "cleared",
    reason?: string
  ) {
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.decideDocument(token, d.id, { doc_type: docType, decision, reason });
      onChanged();
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Document update failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }

  async function verify(patch: Record<string, boolean | string>) {
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.verify(token, d.id, patch);
      onChanged();
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Verify failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }
  async function action(type: string) {
    setBusy(true);
    try {
      const token = await getApiToken();
      const res = await drivers.action(token, d.id, { type });
      if (res.delivery_status === "logged") {
        setToast(
          `${titleCase(type)} logged only — not delivered` + (res.detail ? ` (${res.detail})` : ".")
        );
      } else {
        setToast(`${titleCase(type)} queued.`);
      }
      setTimeout(() => setToast(null), 3500);
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Action failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }
  async function resendInvite() {
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.invite(token, d.id);
      setToast("Invite resent.");
      setTimeout(() => setToast(null), 2500);
      onChanged();
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Invite failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title="Verification & compliance">
        <div className="space-y-2 p-5">
          {canWrite ? (
            <>
              <ToggleRow
                label="License verified"
                value={d.license_verified}
                onToggle={() => void decide("license", d.license_verified ? "cleared" : "verified")}
                busy={busy}
              />
              <ToggleRow
                label="Insurance verified"
                value={d.insurance_verified}
                onToggle={() =>
                  void decide("insurance", d.insurance_verified ? "cleared" : "verified")
                }
                busy={busy}
              />
              <ToggleRow
                label="Vehicle verified"
                value={d.vehicle_verified}
                onToggle={() =>
                  void decide("vehicle_registration", d.vehicle_verified ? "cleared" : "verified")
                }
                busy={busy}
              />
              <ToggleRow
                label="Medical transport certified"
                value={Boolean(d.medical_transport_certified)}
                onToggle={() =>
                  verify({ medical_transport_certified: !d.medical_transport_certified })
                }
                busy={busy}
              />
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-primary">Background check</span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="px-2 py-1 text-xs"
                    onClick={() => void decide("background_check", "verified")}
                    disabled={busy}
                  >
                    Pass
                  </Button>
                  <Button
                    variant="outline"
                    className="px-2 py-1 text-xs"
                    onClick={() =>
                      void decide("background_check", "rejected", "Background check failed.")
                    }
                    disabled={busy}
                  >
                    Fail
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted">
              License {d.license_verified ? "verified" : "not verified"}. Insurance{" "}
              {d.insurance_verified ? "verified" : "not verified"}. Vehicle{" "}
              {d.vehicle_verified ? "verified" : "not verified"}. Background{" "}
              {d.background_check_status || "pending"}.
            </p>
          )}
          {toast && <p className="text-sm text-muted">{toast}</p>}
        </div>
      </SectionCard>
      {canWrite && (
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
            <Button variant="outline" onClick={resendInvite} disabled={busy}>
              <Mail className="h-4 w-4" /> Resend invite
            </Button>
          </div>
        </SectionCard>
      )}
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
