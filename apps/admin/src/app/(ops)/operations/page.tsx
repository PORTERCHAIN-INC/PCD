"use client";

import { useEffect, useRef, useState } from "react";
import {
  Activity as ActivityIcon,
  AlertTriangle,
  Boxes,
  ClipboardList,
  Clock,
  ExternalLink,
  LayoutGrid,
  MapPin,
  Package,
  Pause,
  Play,
  Radio,
  Search,
  Sparkles,
  Timer,
  Truck,
  Users,
  Wallet,
  Zap,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import {
  ops,
  BOARD_ACCENT,
  BOARD_LABELS,
  SLA_TONE,
  type AssignableDriver,
  type OpsOrder,
} from "@/lib/operations";
import {
  Badge,
  Button,
  EmptyState,
  SectionCard,
  Select,
  Spinner,
} from "@/components/crm/primitives";
import { money, relativeTime, titleCase, dateTime } from "@/lib/crmFormat";

const STATE_TONE = (sla: string) => SLA_TONE[sla] ?? "slate";

type TabId = "board" | "orders" | "queue" | "exceptions" | "sla" | "ai" | "activity" | "map";
const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "board", label: "Dispatch Board", icon: LayoutGrid },
  { id: "orders", label: "Active Orders", icon: Package },
  { id: "queue", label: "Dispatch Queue", icon: ClipboardList },
  { id: "exceptions", label: "Exceptions", icon: AlertTriangle },
  { id: "sla", label: "SLA Monitor", icon: Timer },
  { id: "ai", label: "AI Ops", icon: Sparkles },
  { id: "activity", label: "Live Activity", icon: ActivityIcon },
  { id: "map", label: "Live Map", icon: MapPin },
];

export default function OperationsPage() {
  const { getApiToken } = useAdminAuth();
  const [tab, setTab] = useState<TabId>("board");
  const [auto, setAuto] = useState(true);
  const [tick, setTick] = useState(0);
  const [updatedAt, setUpdatedAt] = useState<Date>(new Date());
  const [ssoLoading, setSsoLoading] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const { data: stats } = useApiData((t) => ops.stats(t), [tick]);

  useEffect(() => {
    if (auto) {
      timer.current = setInterval(() => setTick((x) => x + 1), 15000);
      return () => {
        if (timer.current) clearInterval(timer.current);
      };
    }
  }, [auto]);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- stamp last-refresh time whenever the polling tick advances
  useEffect(() => {
    setUpdatedAt(new Date());
  }, [tick]);

  async function openFleetbase() {
    setSsoLoading(true);
    try {
      const token = await getApiToken();
      const session = await api.fleetbaseSso(token);
      window.open(session.console_url, "_blank", "noopener,noreferrer");
    } finally {
      setSsoLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-primary">
            <Radio className="h-5 w-5 text-secondary" /> Operations Control Tower
          </h1>
          <p className="text-sm text-muted">
            Real-time view of dispatch, deliveries, exceptions and SLA across the network.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs text-muted">
            <Clock className="h-3.5 w-3.5" /> Updated {updatedAt.toLocaleTimeString("en-CA")}
          </span>
          <Button variant="outline" onClick={() => setAuto((a) => !a)} className="text-xs">
            {auto ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            {auto ? "Live" : "Paused"}
          </Button>
          <Button variant="outline" onClick={() => setTick((x) => x + 1)} className="text-xs">
            Refresh
          </Button>
          <Button onClick={openFleetbase} disabled={ssoLoading}>
            <ExternalLink className="h-4 w-4" /> {ssoLoading ? "Opening…" : "Fleetbase Console"}
          </Button>
        </div>
      </div>

      {/* KPI grid */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
          <Kpi icon={Package} label="Orders today" value={String(stats.orders_today)} />
          <Kpi
            icon={Truck}
            label="Active deliveries"
            value={String(stats.active_deliveries)}
            accent="text-secondary"
          />
          <Kpi
            icon={ClipboardList}
            label="Waiting dispatch"
            value={String(stats.waiting_dispatch)}
            accent="text-amber-600"
          />
          <Kpi
            icon={Zap}
            label="Delayed"
            value={String(stats.delayed_orders)}
            accent="text-red-600"
          />
          <Kpi
            icon={AlertTriangle}
            label="High priority"
            value={String(stats.high_priority_orders)}
            accent="text-red-600"
          />
          <Kpi
            icon={Users}
            label="Drivers online"
            value={String(stats.drivers_online)}
            accent="text-green-600"
          />
          <Kpi icon={Truck} label="Vehicles active" value={String(stats.vehicles_active)} />
          <Kpi
            icon={Wallet}
            label="Revenue today"
            value={money(stats.revenue_today_cents)}
            accent="text-secondary"
          />
          <Kpi icon={MapPin} label="Pending pickups" value={String(stats.pending_pickups)} />
          <Kpi icon={MapPin} label="Pending deliveries" value={String(stats.pending_deliveries)} />
          <Kpi
            icon={AlertTriangle}
            label="Failed"
            value={String(stats.failed_deliveries)}
            accent="text-red-600"
          />
          <Kpi
            icon={Boxes}
            label="Completed today"
            value={String(stats.completed_today)}
            accent="text-green-600"
          />
          <Kpi
            icon={AlertTriangle}
            label="Open exceptions"
            value={String(stats.open_exceptions)}
            accent="text-amber-600"
          />
          <Kpi icon={AlertTriangle} label="Open claims" value={String(stats.open_claims)} />
          <Kpi icon={ClipboardList} label="Support tickets" value={String(stats.support_tickets)} />
          <Kpi icon={Users} label="Drivers offline" value={String(stats.drivers_offline)} />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto rounded-2xl border border-primary/10 bg-white p-1.5">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
              tab === id ? "bg-secondary text-white" : "text-primary/70 hover:bg-gray-bg"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "board" && <BoardTab tick={tick} />}
      {tab === "orders" && <OrdersTab tick={tick} />}
      {tab === "queue" && <QueueTab tick={tick} onAssigned={() => setTick((x) => x + 1)} />}
      {tab === "exceptions" && <ExceptionsTab tick={tick} />}
      {tab === "sla" && <SlaTab tick={tick} />}
      {tab === "ai" && <AiTab tick={tick} />}
      {tab === "activity" && <ActivityTab tick={tick} />}
      {tab === "map" && <MapTab tick={tick} onFleetbase={openFleetbase} />}
    </div>
  );
}

function Kpi({
  icon: Icon,
  label,
  value,
  accent = "text-primary",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border border-primary/10 bg-white p-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-medium text-muted">{label}</p>
        <Icon className={`h-3.5 w-3.5 ${accent}`} />
      </div>
      <p className="mt-1 text-lg font-bold text-primary">{value}</p>
    </div>
  );
}

function SlaBadge({ sla }: { sla: string }) {
  return <Badge tone={STATE_TONE(sla)}>{sla === "at_risk" ? "At risk" : titleCase(sla)}</Badge>;
}

function OrderCard({ o }: { o: OpsOrder }) {
  return (
    <div className="rounded-xl border border-primary/10 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-xs font-semibold text-primary">{o.tracking_number}</span>
        {o.high_priority && <Badge tone="red">High</Badge>}
      </div>
      <p className="mt-1 truncate text-xs text-muted">{o.merchant ?? "—"}</p>
      <p className="mt-1 truncate text-xs text-primary">
        {o.pickup ?? "?"} → {o.dropoff ?? "?"}
      </p>
      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-muted">{o.driver ?? "Unassigned"}</span>
        <SlaBadge sla={o.sla} />
      </div>
    </div>
  );
}

function BoardTab({ tick }: { tick: number }) {
  const { data } = useApiData((t) => ops.board(t), [tick]);
  if (!data) return <Spinner label="Loading board…" />;
  return (
    <div className="flex gap-3 overflow-x-auto pb-3">
      {data.map((col) => (
        <div key={col.key} className="flex w-64 shrink-0 flex-col">
          <div className="mb-2 flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ background: BOARD_ACCENT[col.key] }}
              />
              <span className="text-sm font-semibold text-primary">
                {BOARD_LABELS[col.key] ?? col.key}
              </span>
              <span className="rounded-full bg-gray-bg px-1.5 text-xs text-muted">{col.count}</span>
            </div>
          </div>
          <div className="flex min-h-[50vh] flex-col gap-2 rounded-2xl border border-dashed border-primary/10 bg-gray-bg/40 p-2">
            {col.orders.map((o) => (
              <OrderCard key={o.id} o={o} />
            ))}
            {col.hidden > 0 && (
              <p className="rounded-lg bg-white/60 px-2 py-2 text-center text-xs text-muted">
                +{col.hidden} more
              </p>
            )}
            {col.orders.length === 0 && (
              <p className="px-2 py-6 text-center text-xs text-muted">Empty</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function OrdersTab({ tick }: { tick: number }) {
  const [search, setSearch] = useState("");
  const { data } = useApiData((t) => ops.orders(t, search || undefined), [tick, search]);
  return (
    <SectionCard
      title="Active orders"
      action={
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tracking…"
            className="w-56 rounded-xl border border-primary/15 py-1.5 pl-9 pr-3 text-sm outline-none focus:border-secondary"
          />
        </div>
      }
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-2">Tracking</th>
              <th className="px-4 py-2">Merchant</th>
              <th className="px-4 py-2">Driver</th>
              <th className="px-4 py-2">Route</th>
              <th className="px-4 py-2">ETA</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">SLA</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((o) => (
              <tr key={o.id} className="border-b border-primary/5">
                <td className="px-4 py-2 font-mono text-xs font-semibold text-primary">
                  {o.tracking_number}
                  {o.high_priority && (
                    <Badge tone="red" className="ml-1">
                      High
                    </Badge>
                  )}
                </td>
                <td className="px-4 py-2">{o.merchant ?? "—"}</td>
                <td className="px-4 py-2">
                  {o.driver ?? <span className="text-muted">Unassigned</span>}
                </td>
                <td className="px-4 py-2 text-xs text-muted">
                  {o.pickup ?? "?"} → {o.dropoff ?? "?"}
                </td>
                <td className="px-4 py-2 text-xs">{o.eta ? dateTime(o.eta) : "—"}</td>
                <td className="px-4 py-2">
                  <Badge tone="sky">{titleCase(o.state)}</Badge>
                </td>
                <td className="px-4 py-2">
                  <SlaBadge sla={o.sla} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!data || data.length === 0) && <EmptyState title="No active orders" />}
      </div>
    </SectionCard>
  );
}

function QueueTab({ tick, onAssigned }: { tick: number; onAssigned: () => void }) {
  const { getApiToken } = useAdminAuth();
  const { data } = useApiData((t) => ops.queue(t), [tick]);
  const { data: driversList } = useApiData((t) => ops.assignableDrivers(t), [tick]);
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);

  async function assign(orderId: string) {
    const driverId = choice[orderId];
    if (!driverId) return;
    setBusy(orderId);
    try {
      const token = await getApiToken();
      await api.assignDriver(token, orderId, driverId);
      onAssigned();
    } finally {
      setBusy(null);
    }
  }

  const online = (driversList ?? []).filter((d) => d.online);

  return (
    <SectionCard
      title={`Dispatch queue (${data?.length ?? 0})`}
      action={<span className="text-xs text-muted">{online.length} drivers online</span>}
    >
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((o) => (
          <div key={o.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
            <div className="min-w-0">
              <p className="font-mono text-xs font-semibold text-primary">
                {o.tracking_number} {o.high_priority && <Badge tone="red">High</Badge>}
              </p>
              <p className="truncate text-xs text-muted">
                {o.merchant ?? "—"} · {o.pickup ?? "?"} → {o.dropoff ?? "?"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <SlaBadge sla={o.sla} />
              <Select
                value={choice[o.id] ?? ""}
                onChange={(e) => setChoice({ ...choice, [o.id]: e.target.value })}
                className="w-48"
              >
                <option value="">Assign driver…</option>
                {(driversList ?? []).map((d: AssignableDriver) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                    {d.online ? " ●" : ""}
                    {d.rating ? ` · ${d.rating}★` : ""}
                  </option>
                ))}
              </Select>
              <Button onClick={() => assign(o.id)} disabled={!choice[o.id] || busy === o.id}>
                Assign
              </Button>
            </div>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <EmptyState title="Queue is clear" hint="No orders awaiting dispatch." />
        )}
      </div>
    </SectionCard>
  );
}

function ExceptionsTab({ tick }: { tick: number }) {
  const { data } = useApiData((t) => ops.exceptions(t), [tick]);
  return (
    <SectionCard title={`Exception center (${data?.length ?? 0})`}>
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((e) => (
          <div key={e.id} className="flex items-center justify-between px-5 py-3">
            <div>
              <p className="text-sm font-medium text-primary">{titleCase(e.type)}</p>
              <p className="text-xs text-muted">
                {e.tracking_number} · {e.merchant ?? "—"} · reported by {titleCase(e.reported_by)} ·{" "}
                {relativeTime(e.created_at)}
              </p>
            </div>
            <Badge tone="amber">{titleCase(e.status)}</Badge>
          </div>
        ))}
        {(!data || data.length === 0) && <EmptyState title="No open exceptions" />}
      </div>
    </SectionCard>
  );
}

function SlaTab({ tick }: { tick: number }) {
  const { data } = useApiData((t) => ops.sla(t), [tick]);
  if (!data) return <Spinner />;
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title={`Breached (${data.breached_count})`}>
        <div className="divide-y divide-primary/5">
          {data.breached.map((o) => (
            <SlaRow key={o.id} o={o} />
          ))}
          {data.breached.length === 0 && <EmptyState title="No SLA breaches" />}
        </div>
      </SectionCard>
      <SectionCard title={`At risk (${data.at_risk_count})`}>
        <div className="divide-y divide-primary/5">
          {data.at_risk.map((o) => (
            <SlaRow key={o.id} o={o} />
          ))}
          {data.at_risk.length === 0 && <EmptyState title="Nothing approaching breach" />}
        </div>
      </SectionCard>
    </div>
  );
}

function SlaRow({ o }: { o: OpsOrder }) {
  return (
    <div className="flex items-center justify-between px-5 py-3">
      <div>
        <p className="font-mono text-xs font-semibold text-primary">{o.tracking_number}</p>
        <p className="text-xs text-muted">
          {o.merchant ?? "—"} · {o.driver ?? "Unassigned"} · ETA {o.eta ? dateTime(o.eta) : "—"}
        </p>
      </div>
      <Badge tone="sky">{titleCase(o.state)}</Badge>
    </div>
  );
}

function AiTab({ tick }: { tick: number }) {
  const { data } = useApiData((t) => ops.ai(t), [tick]);
  if (!data) return <Spinner />;
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <SectionCard title="Risk orders" className="lg:col-span-2">
        <div className="divide-y divide-primary/5">
          {data.risk_orders.map((o) => (
            <div key={o.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="font-mono text-xs font-semibold text-primary">{o.tracking_number}</p>
                <p className="text-xs text-muted">{(o.reasons ?? []).join(" · ")}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={(o.risk_score ?? 0) >= 60 ? "red" : "amber"}>
                  Risk {o.risk_score}
                </Badge>
                <SlaBadge sla={o.sla} />
              </div>
            </div>
          ))}
          {data.risk_orders.length === 0 && (
            <EmptyState title="No risk orders" hint={data.recommendation} />
          )}
        </div>
      </SectionCard>
      <SectionCard title="Dispatch recommendation">
        <div className="p-5">
          <div className="rounded-xl border border-secondary/20 bg-secondary/5 p-3 text-sm text-primary">
            <Sparkles className="mb-1 h-4 w-4 text-secondary" />
            {data.recommendation}
          </div>
          <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-muted">
            Suggested drivers
          </p>
          <div className="space-y-2">
            {data.suggested_drivers.map((d) => (
              <div
                key={d.id}
                className="flex items-center justify-between rounded-lg border border-primary/10 px-3 py-2 text-sm"
              >
                <span className="text-primary">{d.name}</span>
                <span className="text-xs text-muted">
                  {d.rating ? `${d.rating}★` : ""} {d.online ? "● online" : ""}
                </span>
              </div>
            ))}
            {data.suggested_drivers.length === 0 && (
              <p className="text-sm text-muted">No drivers online.</p>
            )}
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

function ActivityTab({ tick }: { tick: number }) {
  const { data } = useApiData((t) => ops.activity(t), [tick]);
  return (
    <SectionCard title="Live activity">
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((e) => (
          <div key={e.id} className="flex items-center justify-between px-5 py-2.5">
            <div className="flex items-center gap-3">
              <span className="h-2 w-2 rounded-full bg-secondary" />
              <div>
                <p className="text-sm text-primary">
                  {titleCase(e.event_type.replace(/\./g, " "))}
                </p>
                <p className="text-xs text-muted">
                  {titleCase(e.aggregate_type)} · {titleCase(e.actor_type)}
                </p>
              </div>
            </div>
            <span className="text-xs text-muted">{relativeTime(e.occurred_at)}</span>
          </div>
        ))}
        {(!data || data.length === 0) && <EmptyState title="No recent activity" />}
      </div>
    </SectionCard>
  );
}

function MapTab({ tick, onFleetbase }: { tick: number; onFleetbase: () => void }) {
  const { data } = useApiData((t) => ops.map(t), [tick]);
  if (!data) return <Spinner />;
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <SectionCard title="Live network" className="lg:col-span-2">
        <div
          className="relative m-5 overflow-hidden rounded-2xl border border-primary/10"
          style={{ height: 360, background: "linear-gradient(135deg,#eaf1fb,#f6f9ff)" }}
        >
          <div
            className="absolute inset-0 opacity-40"
            style={{
              backgroundImage: "radial-gradient(#2563eb22 1px, transparent 1px)",
              backgroundSize: "22px 22px",
            }}
          />
          {data.orders.slice(0, 40).map((o, i) => (
            <span
              key={o.order_id}
              title={`${o.tracking} · ${o.state}`}
              className="absolute flex h-6 w-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-secondary text-white shadow"
              style={{ left: `${10 + ((i * 37) % 80)}%`, top: `${12 + ((i * 53) % 76)}%` }}
            >
              <Truck className="h-3 w-3" />
            </span>
          ))}
          <div className="absolute bottom-3 left-3 rounded-lg bg-white/90 px-3 py-1.5 text-xs text-muted shadow">
            {data.orders.length} in-flight · {data.drivers.length} drivers online
          </div>
        </div>
        <p className="px-5 pb-4 text-xs text-muted">
          {data.fleetbase_note}. Full Google Maps + live GPS render from Fleetbase tracking via the
          Porterchain bridge —{" "}
          <button onClick={onFleetbase} className="font-medium text-secondary underline">
            open the Fleetbase console
          </button>{" "}
          for the operational map.
        </p>
      </SectionCard>
      <SectionCard title="Online drivers">
        <div className="divide-y divide-primary/5">
          {data.drivers.map((d) => (
            <div key={d.id} className="flex items-center justify-between px-5 py-3">
              <span className="text-sm text-primary">{d.name}</span>
              <Badge tone={d.online ? "green" : "slate"}>{titleCase(d.status)}</Badge>
            </div>
          ))}
          {data.drivers.length === 0 && <EmptyState title="No drivers online" />}
        </div>
      </SectionCard>
    </div>
  );
}
