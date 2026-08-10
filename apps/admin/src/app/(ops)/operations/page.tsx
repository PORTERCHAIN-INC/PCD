"use client";

import { useEffect, useRef, useState } from "react";
import {
  Activity as ActivityIcon,
  AlertTriangle,
  CalendarDays,
  ClipboardList,
  Clock,
  Gauge,
  LayoutDashboard,
  LayoutGrid,
  Map,
  Monitor,
  Moon,
  Package,
  Pause,
  Play,
  Radio,
  Users,
  Sparkles,
  Timer,
  Plus,
  Volume2,
  VolumeX,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { ops, type OpsOrder } from "@/lib/operations";
import { DispatchBoard } from "@/components/operations/DispatchBoard";
import { DispatchQueuePanel } from "@/components/operations/DispatchQueuePanel";
import { KpiStrip } from "@/components/operations/KpiStrip";
import { LiveMapPanel } from "@/components/operations/LiveMapPanel";
import { adaptivePollMs, OpsAlertToast } from "@/components/operations/OpsAlertToast";
import { DispatcherCopilotPanel } from "@/components/operations/DispatcherCopilotPanel";
import { OptimizePanel } from "@/components/operations/OptimizePanel";
import { OpsCommandPalette } from "@/components/operations/OpsCommandPalette";
import { OrdersTablePanel } from "@/components/operations/OrdersTablePanel";
import { ScheduledBatchesPanel } from "@/components/operations/ScheduledBatchesPanel";
import { UtilizationPanel } from "@/components/operations/UtilizationPanel";
import { Order360Drawer } from "@/components/orders/Order360Drawer";
import { OrderBuilderModal } from "@/components/orders/OrderBuilderModal";
import { AssignDriverModal } from "@/components/orders/AssignDriverModal";
import {
  ExceptionReasonModal,
  isExceptionColumn,
  type ExceptionColumn,
} from "@/components/orders/ExceptionReasonModal";
import OpenFleetbaseButton from "@/components/nav/OpenFleetbaseButton";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { relativeTime, titleCase, dateTime } from "@/lib/crmFormat";

type TabId =
  | "overview"
  | "board"
  | "map"
  | "orders"
  | "queue"
  | "scheduled"
  | "optimize"
  | "exceptions"
  | "sla"
  | "ai"
  | "activity"
  | "utilization";
const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "board", label: "Dispatch Board", icon: LayoutGrid },
  { id: "map", label: "Live Map", icon: Map },
  { id: "orders", label: "Active Orders", icon: Package },
  { id: "queue", label: "Dispatch Queue", icon: ClipboardList },
  { id: "scheduled", label: "Scheduled", icon: CalendarDays },
  { id: "optimize", label: "Optimize", icon: Gauge },
  { id: "utilization", label: "Utilization", icon: Users },
  { id: "exceptions", label: "Exceptions", icon: AlertTriangle },
  { id: "sla", label: "SLA Monitor", icon: Timer },
  { id: "ai", label: "Copilot", icon: Sparkles },
  { id: "activity", label: "Live Activity", icon: ActivityIcon },
];

type OpsDisplay = "default" | "dark" | "wall";
const DISPLAY_KEY = "porterchain.ops.display";

export default function OperationsPage() {
  const [tab, setTab] = useState<TabId>("overview");
  const [auto, setAuto] = useState(true);
  const [sound, setSound] = useState(false);
  const [display, setDisplay] = useState<OpsDisplay>("default");
  const [tick, setTick] = useState(0);
  const [updatedAt, setUpdatedAt] = useState<Date>(new Date());
  const [drawerOrderId, setDrawerOrderId] = useState<string | null>(null);
  const [builderOpen, setBuilderOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem(DISPLAY_KEY);
    if (raw === "dark" || raw === "wall" || raw === "default") setDisplay(raw);
  }, []);

  const cycleDisplay = () => {
    const next: OpsDisplay =
      display === "default" ? "dark" : display === "dark" ? "wall" : "default";
    setDisplay(next);
    localStorage.setItem(DISPLAY_KEY, next);
  };

  const openOrder = (id: string) => setDrawerOrderId(id);
  const refresh = () => setTick((x) => x + 1);

  const { data: stats } = useApiData((t) => ops.stats(t), [tick], { key: "ops-stats" });
  const pollMs = adaptivePollMs(stats);

  useEffect(() => {
    if (!auto) return;
    timer.current = setInterval(() => setTick((x) => x + 1), pollMs);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [auto, pollMs]);
  useEffect(() => {
    setUpdatedAt(new Date());
  }, [tick]);

  return (
    <div
      className={cn(
        "ops-tower space-y-4",
        display === "dark" && "ops-tower--dark",
        display === "wall" && "ops-tower--dark ops-tower--wall"
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-primary">
            <Radio className="h-5 w-5 text-secondary" /> Operations Control Tower
          </h1>
          {display !== "wall" && (
            <p className="text-sm text-muted">
              Real-time view of dispatch, deliveries, exceptions and SLA across the network.
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <span className="flex items-center gap-1.5 text-xs text-muted">
            <Clock className="h-3.5 w-3.5" /> Updated {updatedAt.toLocaleTimeString("en-CA")}
            {auto && <span className="text-muted/70">· every {Math.round(pollMs / 1000)}s</span>}
          </span>
          <Button variant="outline" onClick={cycleDisplay} className="text-xs" title="Display mode">
            {display === "wall" ? (
              <Monitor className="h-4 w-4" />
            ) : display === "dark" ? (
              <Moon className="h-4 w-4" />
            ) : (
              <Monitor className="h-4 w-4" />
            )}
            {display === "default" ? "Light" : display === "dark" ? "Dark" : "Wall"}
          </Button>
          <Button variant="outline" onClick={() => setSound((s) => !s)} className="text-xs">
            {sound ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
            {sound ? "Sound on" : "Sound off"}
          </Button>
          <Button variant="outline" onClick={() => setAuto((a) => !a)} className="text-xs">
            {auto ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            {auto ? "Live" : "Paused"}
          </Button>
          <Button variant="outline" onClick={() => setTick((x) => x + 1)} className="text-xs">
            Refresh
          </Button>
          {display !== "wall" && (
            <Button onClick={() => setBuilderOpen(true)} className="text-xs">
              <Plus className="h-4 w-4" /> New order
            </Button>
          )}
          {display !== "wall" && <OpenFleetbaseButton variant="toolbar" />}
        </div>
      </div>

      {stats && <KpiStrip stats={stats} onDrill={(t) => setTab(t)} />}

      {/* Tabs */}
      <div className="ops-table-scroll flex gap-1 rounded-2xl border border-primary/10 bg-white p-1.5 ops-tower-tabs">
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

      {tab === "overview" && (
        <OverviewTab tick={tick} onAssigned={refresh} onOpenOrder={openOrder} />
      )}
      {tab === "board" && <BoardTab tick={tick} onMoved={refresh} onOpenOrder={openOrder} />}
      {tab === "map" && <LiveMapPanel tick={tick} onOpenOrder={openOrder} />}
      {tab === "orders" && <OrdersTablePanel tick={tick} onOpenOrder={openOrder} />}
      {tab === "queue" && (
        <DispatchQueuePanel tick={tick} onAssigned={refresh} onOpenOrder={openOrder} />
      )}
      {tab === "scheduled" && <ScheduledBatchesPanel tick={tick} onOpenOrder={openOrder} />}
      {tab === "optimize" && (
        <OptimizePanel tick={tick} onOpenOrder={openOrder} onCommitted={refresh} />
      )}
      {tab === "utilization" && <UtilizationPanel tick={tick} />}
      {tab === "exceptions" && <ExceptionsTab tick={tick} onOpenOrder={openOrder} />}
      {tab === "sla" && <SlaTab tick={tick} onOpenOrder={openOrder} />}
      {tab === "ai" && (
        <DispatcherCopilotPanel tick={tick} onOpenOrder={openOrder} onChanged={refresh} />
      )}
      {tab === "activity" && (
        <ActivityTab tick={tick} followOrderId={drawerOrderId} onOpenOrder={openOrder} />
      )}

      <Order360Drawer
        orderId={drawerOrderId}
        onClose={() => setDrawerOrderId(null)}
        onChanged={refresh}
      />
      <OrderBuilderModal
        open={builderOpen}
        onClose={() => setBuilderOpen(false)}
        onCreated={(id) => {
          refresh();
          openOrder(id);
        }}
      />
      <OpsCommandPalette onOpenOrder={openOrder} />
      <OpsAlertToast stats={stats} soundEnabled={sound} />
    </div>
  );
}

function OverviewTab({
  tick,
  onAssigned,
  onOpenOrder,
}: {
  tick: number;
  onAssigned: () => void;
  onOpenOrder: (id: string) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <DispatchQueuePanel tick={tick} onAssigned={onAssigned} onOpenOrder={onOpenOrder} />
        <LiveMapPanel tick={tick} onOpenOrder={onOpenOrder} />
      </div>
      <ActivityTab tick={tick} compact />
    </div>
  );
}

function BoardTab({
  tick,
  onMoved,
  onOpenOrder,
}: {
  tick: number;
  onMoved: () => void;
  onOpenOrder: (id: string) => void;
}) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => ops.board(t), [tick], { key: "ops-board" });
  const [error, setError] = useState<string | null>(null);
  const [assignOrder, setAssignOrder] = useState<OpsOrder | null>(null);
  const [exceptionTarget, setExceptionTarget] = useState<{
    order: OpsOrder;
    column: ExceptionColumn;
  } | null>(null);

  async function move(order: OpsOrder, toColumn: string, reason?: string) {
    setError(null);
    try {
      const token = await getApiToken();
      await ops.moveBoardOrder(token, order.id, toColumn, reason);
      onMoved();
      await refetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not move order — invalid transition path.");
      throw e;
    }
  }

  function requestMove(order: OpsOrder, toColumn: string) {
    setError(null);
    if (toColumn === "assigned") {
      setAssignOrder(order);
      return;
    }
    if (isExceptionColumn(toColumn)) {
      setExceptionTarget({ order, column: toColumn });
      return;
    }
    setError(
      "Execution columns (accept → delivered) advance in Fleetbase / the driver app. Use Assign for drivers, or Order 360 for exceptions."
    );
  }

  if (!data) return <Spinner label="Loading board…" />;

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted">
        Click a card to open Order 360. Drop on <strong>Assigned</strong> to pick a driver, or on
        Failed / Returned / Lost / Damaged to enter a reason. Accept → Deliver stays in Fleetbase.
      </p>
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}
      <DispatchBoard
        columns={data}
        onMove={(o, col) => move(o, col)}
        onRequestMove={requestMove}
        onOpenOrder={(o) => onOpenOrder(o.id)}
      />
      <AssignDriverModal
        open={!!assignOrder}
        orderId={assignOrder?.id ?? null}
        trackingNumber={assignOrder?.tracking_number}
        currentDriverName={assignOrder?.driver}
        onClose={() => setAssignOrder(null)}
        onAssigned={() => {
          onMoved();
          void refetch();
        }}
      />
      <ExceptionReasonModal
        open={!!exceptionTarget}
        trackingNumber={exceptionTarget?.order.tracking_number}
        initialColumn={exceptionTarget?.column ?? ""}
        allowColumnChange={false}
        onClose={() => setExceptionTarget(null)}
        onConfirm={async (column, reason) => {
          if (!exceptionTarget) return;
          await move(exceptionTarget.order, column, reason);
        }}
      />
    </div>
  );
}

function ExceptionAgeBadge({ createdAt }: { createdAt: string | null }) {
  if (!createdAt) return null;
  const hrs = (Date.now() - new Date(createdAt).getTime()) / 3_600_000;
  const tone = hrs >= 4 ? "red" : hrs >= 1 ? "amber" : "slate";
  return <Badge tone={tone}>{relativeTime(createdAt)}</Badge>;
}

function ExceptionsTab({ tick, onOpenOrder }: { tick: number; onOpenOrder: (id: string) => void }) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => ops.exceptions(t), [tick], { key: "ops-exceptions" });
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [note, setNote] = useState("");

  async function run(id: string, fn: (token: string) => Promise<unknown>) {
    setBusy(id);
    setActionError(null);
    try {
      const token = await getApiToken();
      await fn(token);
      setResolvingId(null);
      setNote("");
      await refetch();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-3">
      {actionError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {actionError}
        </p>
      )}
      <SectionCard title={`Exception center (${data?.length ?? 0})`}>
        <div className="divide-y divide-primary/5">
          {(data ?? []).map((e) => (
            <div key={e.id} className="px-5 py-3">
              <div className="flex items-start justify-between gap-3">
                <div
                  onClick={() => onOpenOrder(e.order_id)}
                  className="min-w-0 flex-1 cursor-pointer rounded-lg px-2 py-1 -mx-2 -my-1 transition-colors hover:bg-gray-bg/70"
                  title="Open Order 360"
                >
                  <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-primary">
                    {titleCase(e.type)}
                    <ExceptionAgeBadge createdAt={e.created_at} />
                  </p>
                  <p className="text-xs text-muted">
                    <span className="font-mono">{e.tracking_number}</span> · {e.merchant ?? "—"} ·
                    reported by {titleCase(e.reported_by)}
                    {e.order_state ? ` · order ${titleCase(e.order_state)}` : ""}
                  </p>
                  {e.acknowledged_by && (
                    <p className="mt-0.5 text-[11px] text-muted">
                      Acknowledged by {e.acknowledged_by} {relativeTime(e.acknowledged_at)}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                  <Badge tone={e.status === "acknowledged" ? "blue" : "amber"}>
                    {titleCase(e.status)}
                  </Badge>
                  {e.status === "open" && (
                    <Button
                      variant="outline"
                      className="px-3 py-1.5 text-xs"
                      disabled={busy === e.id}
                      onClick={() => void run(e.id, (t) => ops.acknowledgeException(t, e.id))}
                    >
                      Acknowledge
                    </Button>
                  )}
                  {e.order_state === "FAILED" && (
                    <Button
                      variant="outline"
                      className="px-3 py-1.5 text-xs"
                      disabled={busy === e.id}
                      onClick={() => void run(e.id, (t) => ops.retryException(t, e.id))}
                    >
                      Retry dispatch
                    </Button>
                  )}
                  <Button
                    className="px-3 py-1.5 text-xs"
                    disabled={busy === e.id}
                    onClick={() => {
                      setResolvingId(resolvingId === e.id ? null : e.id);
                      setNote("");
                    }}
                  >
                    Resolve
                  </Button>
                  {e.customer_email && (
                    <a
                      href={`mailto:${e.customer_email}?subject=Delivery ${e.tracking_number}`}
                      className="inline-flex items-center gap-1 rounded-xl border border-primary/15 bg-white px-3 py-1.5 text-xs font-medium text-primary hover:bg-gray-bg"
                    >
                      Contact
                    </a>
                  )}
                </div>
              </div>
              {resolvingId === e.id && (
                <div className="mt-2 flex items-center gap-2 pl-2">
                  <input
                    value={note}
                    onChange={(ev) => setNote(ev.target.value)}
                    placeholder="Resolution note (optional)…"
                    className="w-72 rounded-xl border border-primary/15 px-3 py-1.5 text-sm outline-none focus:border-secondary"
                  />
                  <Button
                    className="px-3 py-1.5 text-xs"
                    disabled={busy === e.id}
                    onClick={() =>
                      void run(e.id, (t) => ops.resolveException(t, e.id, note || undefined))
                    }
                  >
                    Confirm resolve
                  </Button>
                  <Button
                    variant="ghost"
                    className="px-3 py-1.5 text-xs"
                    onClick={() => {
                      setResolvingId(null);
                      setNote("");
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              )}
            </div>
          ))}
          {(!data || data.length === 0) && <EmptyState title="No open exceptions" />}
        </div>
      </SectionCard>
    </div>
  );
}

function SlaTab({ tick, onOpenOrder }: { tick: number; onOpenOrder: (id: string) => void }) {
  const { data } = useApiData((t) => ops.sla(t), [tick], { key: "ops-sla" });
  if (!data) return <Spinner />;
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title={`Breached (${data.breached_count})`}>
        <div className="divide-y divide-primary/5">
          {data.breached.map((o) => (
            <SlaRow key={o.id} o={o} onOpen={() => onOpenOrder(o.id)} />
          ))}
          {data.breached.length === 0 && <EmptyState title="No SLA breaches" />}
        </div>
      </SectionCard>
      <SectionCard title={`At risk (${data.at_risk_count})`}>
        <div className="divide-y divide-primary/5">
          {data.at_risk.map((o) => (
            <SlaRow key={o.id} o={o} onOpen={() => onOpenOrder(o.id)} />
          ))}
          {data.at_risk.length === 0 && <EmptyState title="Nothing approaching breach" />}
        </div>
      </SectionCard>
    </div>
  );
}

function SlaRow({ o, onOpen }: { o: OpsOrder; onOpen?: () => void }) {
  return (
    <div
      onClick={onOpen}
      className={cn(
        "flex items-center justify-between px-5 py-3",
        onOpen && "cursor-pointer transition-colors hover:bg-gray-bg/60"
      )}
      title={onOpen ? "Open Order 360" : undefined}
    >
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

const FOLLOW_KEY = "porterchain.ops.followOrderIds";

function readFollowed(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(FOLLOW_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function writeFollowed(ids: string[]) {
  localStorage.setItem(FOLLOW_KEY, JSON.stringify(ids.slice(0, 20)));
}

function ActivityTab({
  tick,
  compact,
  followOrderId,
  onOpenOrder,
}: {
  tick: number;
  compact?: boolean;
  followOrderId?: string | null;
  onOpenOrder?: (id: string) => void;
}) {
  const { data } = useApiData((t) => ops.activity(t), [tick], { key: "ops-activity" });
  const [followed, setFollowed] = useState<string[]>(() => readFollowed());
  const [followOnly, setFollowOnly] = useState(false);

  useEffect(() => {
    writeFollowed(followed);
  }, [followed]);

  function toggleFollow(orderId: string) {
    setFollowed((prev) =>
      prev.includes(orderId) ? prev.filter((id) => id !== orderId) : [...prev, orderId]
    );
  }

  const filtered = (data ?? []).filter((e) =>
    followOnly && followed.length ? followed.includes(e.aggregate_id) : true
  );
  const rows = compact ? filtered.slice(0, 8) : filtered;

  return (
    <SectionCard
      title={compact ? "Live activity feed" : "Live activity"}
      action={
        !compact ? (
          <div className="flex items-center gap-2">
            {followOrderId && (
              <Button
                variant="outline"
                className="text-xs"
                onClick={() => toggleFollow(followOrderId)}
              >
                {followed.includes(followOrderId) ? "Unfollow open order" : "Follow open order"}
              </Button>
            )}
            <Button
              variant={followOnly ? "primary" : "outline"}
              className="text-xs"
              onClick={() => setFollowOnly((v) => !v)}
              disabled={!followed.length}
            >
              Follow mode {followed.length ? `(${followed.length})` : ""}
            </Button>
          </div>
        ) : undefined
      }
    >
      <div className={cn("divide-y divide-primary/5", compact && "max-h-64 overflow-y-auto")}>
        {rows.map((e) => (
          <div key={e.id} className="flex items-center justify-between px-5 py-2.5">
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "h-2 w-2 rounded-full",
                  followed.includes(e.aggregate_id) ? "bg-amber-500" : "bg-secondary"
                )}
              />
              <div>
                <p className="text-sm text-primary">
                  {titleCase(e.event_type.replace(/\./g, " "))}
                </p>
                <p className="text-xs text-muted">
                  {titleCase(e.aggregate_type)} · {titleCase(e.actor_type)}
                  {e.aggregate_type === "order" && onOpenOrder ? (
                    <>
                      {" · "}
                      <button
                        type="button"
                        className="text-secondary hover:underline"
                        onClick={() => onOpenOrder(e.aggregate_id)}
                      >
                        open
                      </button>
                      {" · "}
                      <button
                        type="button"
                        className="text-muted hover:underline"
                        onClick={() => toggleFollow(e.aggregate_id)}
                      >
                        {followed.includes(e.aggregate_id) ? "unfollow" : "follow"}
                      </button>
                    </>
                  ) : null}
                </p>
              </div>
            </div>
            <span className="text-xs text-muted">{relativeTime(e.occurred_at)}</span>
          </div>
        ))}
        {rows.length === 0 && (
          <EmptyState
            title={followOnly ? "No followed-order events" : "No recent activity"}
            hint={followOnly ? "Follow orders from this feed or Order 360." : undefined}
          />
        )}
      </div>
    </SectionCard>
  );
}
