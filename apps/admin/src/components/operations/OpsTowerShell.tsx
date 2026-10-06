"use client";

import { useEffect, useEffectEvent, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  CalendarDays,
  ChevronDown,
  Clock,
  Gauge,
  LayoutDashboard,
  LayoutGrid,
  Monitor,
  Moon,
  Package,
  Pause,
  Play,
  Plus,
  Radio,
  Sparkles,
  Users,
  Volume2,
  VolumeX,
  Wrench,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import AdminPage from "@/components/layout/AdminPage";
import OpsPageHero from "@/components/layout/OpsPageHero";
import { useApiData } from "@/hooks/useApiData";
import { ops } from "@/lib/operations";
import { OpsPressureBar } from "@/components/operations/OpsPressureBar";
import { PushHealthStrip } from "@/components/operations/PushHealthStrip";
import { SyncHealthStrip } from "@/components/operations/SyncHealthStrip";
import { adaptivePollMs, OpsAlertToast } from "@/components/operations/OpsAlertToast";
import { OpsCommandPalette } from "@/components/operations/OpsCommandPalette";
import { OpsDeskLayout } from "@/components/operations/OpsDeskLayout";
import { BoardPanel } from "@/components/operations/BoardPanel";
import { AttentionPanel } from "@/components/operations/AttentionPanel";
import { OrdersTablePanel } from "@/components/operations/OrdersTablePanel";
import { ScheduledBatchesPanel } from "@/components/operations/ScheduledBatchesPanel";
import { OptimizePanel } from "@/components/operations/OptimizePanel";
import { UtilizationPanel } from "@/components/operations/UtilizationPanel";
import { DispatcherCopilotPanel } from "@/components/operations/DispatcherCopilotPanel";
import { Button } from "@/components/crm/primitives";
import { Order360Drawer } from "@/components/orders/Order360Drawer";
import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const OrderBuilderModal = dynamic(
  () =>
    import("@/components/orders/OrderBuilderModal").then((m) => ({
      default: m.OrderBuilderModal,
    })),
  { loading: () => <PageSkeleton rows={3} />, ssr: false }
);
import {
  parseOpsSearchParams,
  writeOpsSearchParams,
  type OpsToolId,
  type OpsViewId,
} from "@/components/operations/opsViews";

type OpsDisplay = "default" | "dark" | "wall";
const DISPLAY_KEY = "porterchain.ops.display";

const PRIMARY: {
  id: OpsViewId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  wallHide?: boolean;
}[] = [
  { id: "desk", label: "Desk", icon: LayoutDashboard },
  { id: "board", label: "Board", icon: LayoutGrid },
  { id: "orders", label: "Orders", icon: Package },
  { id: "attention", label: "Attention", icon: AlertTriangle },
  { id: "tools", label: "Tools", icon: Wrench, wallHide: true },
];

const TOOLS: {
  id: OpsToolId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { id: "scheduled", label: "Scheduled", icon: CalendarDays },
  { id: "optimize", label: "Optimize", icon: Gauge },
  { id: "utilization", label: "Utilization", icon: Users },
  { id: "ai", label: "Copilot", icon: Sparkles },
];

export function OpsTowerShell() {
  const searchParams = useSearchParams();
  const initial = parseOpsSearchParams(new URLSearchParams(searchParams?.toString() ?? ""));
  const [view, setView] = useState<OpsViewId>(initial.view);
  const [tool, setTool] = useState<OpsToolId | null>(initial.tool);
  const [toolsOpen, setToolsOpen] = useState(initial.view === "tools");
  const [auto, setAuto] = useState(true);
  const [sound, setSound] = useState(false);
  const [display, setDisplay] = useState<OpsDisplay>("default");
  const [tick, setTick] = useState(0);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [clockReady, setClockReady] = useState(false);
  const [drawerOrderId, setDrawerOrderId] = useState<string | null>(null);
  const [builderOpen, setBuilderOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const urlSyncReady = useRef(false);

  useEffect(() => {
    const raw = localStorage.getItem(DISPLAY_KEY);
    if (raw === "dark" || raw === "wall" || raw === "default") setDisplay(raw);
    urlSyncReady.current = true;
    setUpdatedAt(new Date());
    setClockReady(true);
  }, []);

  useEffect(() => {
    if (!urlSyncReady.current) return;
    writeOpsSearchParams(view, view === "tools" ? tool : null);
  }, [view, tool]);

  useEffect(() => {
    const parsed = parseOpsSearchParams(new URLSearchParams(searchParams?.toString() ?? ""));
    setView(parsed.view);
    setTool(parsed.tool);
    if (parsed.view === "tools") setToolsOpen(true);
  }, [searchParams]);

  const cycleDisplay = () => {
    const next: OpsDisplay =
      display === "default" ? "dark" : display === "dark" ? "wall" : "default";
    setDisplay(next);
    localStorage.setItem(DISPLAY_KEY, next);
    if (next === "wall" && view === "tools") {
      setView("desk");
      setTool(null);
      setToolsOpen(false);
    }
  };

  const openOrder = (id: string) => setDrawerOrderId(id);
  const refresh = () => setTick((x) => x + 1);

  const goView = (next: OpsViewId, nextTool?: OpsToolId | null) => {
    if (next === "tools") {
      setView("tools");
      setTool(nextTool ?? tool ?? "optimize");
      setToolsOpen(true);
      return;
    }
    setView(next);
    setTool(null);
    setToolsOpen(false);
  };

  const { data: stats } = useApiData((t) => ops.stats(t), [tick], { key: "ops-stats" });
  const pollMs = adaptivePollMs(stats);

  const bumpTick = useEffectEvent(() => {
    setTick((x) => x + 1);
  });

  useEffect(() => {
    if (!auto) return;
    timer.current = setInterval(() => bumpTick(), pollMs);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [auto, pollMs]);
  useEffect(() => {
    setUpdatedAt(new Date());
  }, [tick]);

  const wall = display === "wall";
  const activeTool = tool ?? "optimize";

  return (
    <AdminPage className="!space-y-3">
      <div
        className={cn(
          "ops-tower space-y-3",
          display === "dark" && "ops-tower--dark",
          wall && "ops-tower--dark ops-tower--wall"
        )}
      >
        <OpsPageHero
          icon={Radio}
          title="Control Tower"
          description={
            wall ? undefined : "Assign waiting work, clear exceptions, and watch the network live."
          }
          actions={
            <>
              <SyncHealthStrip tick={tick} compactWhenOk />
              <PushHealthStrip tick={tick} compactWhenOk />
              <span
                className="hidden items-center gap-1.5 text-xs text-muted sm:flex"
                suppressHydrationWarning
              >
                <Clock className="h-3.5 w-3.5" />
                {clockReady && updatedAt ? updatedAt.toLocaleTimeString("en-CA") : "—"}
                {auto ? (
                  <span className="text-muted/70">· {Math.round(pollMs / 1000)}s</span>
                ) : null}
              </span>
              <div className="flex items-center gap-1 rounded-xl border border-primary/10 bg-white/80 p-1">
                <Button
                  variant="outline"
                  onClick={cycleDisplay}
                  className="border-0 px-2.5 py-1.5 text-xs shadow-none"
                  title={`Display: ${display}`}
                  aria-label={`Display mode ${display}`}
                >
                  {display === "dark" ? (
                    <Moon className="h-4 w-4" />
                  ) : (
                    <Monitor className="h-4 w-4" />
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setSound((s) => !s)}
                  className="border-0 px-2.5 py-1.5 text-xs shadow-none"
                  title={sound ? "Sound on" : "Sound off"}
                  aria-label={sound ? "Mute alerts" : "Enable sound alerts"}
                >
                  {sound ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setAuto((a) => !a)}
                  className={cn(
                    "border-0 px-2.5 py-1.5 text-xs shadow-none",
                    auto && "bg-secondary/10 text-secondary"
                  )}
                  title={auto ? "Live polling" : "Paused"}
                  aria-label={auto ? "Pause live updates" : "Resume live updates"}
                >
                  {auto ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  <span className="hidden sm:inline">{auto ? "Live" : "Paused"}</span>
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setTick((x) => x + 1)}
                  className="border-0 px-2.5 py-1.5 text-xs shadow-none"
                  aria-label="Refresh now"
                >
                  Refresh
                </Button>
              </div>
              {!wall ? (
                <Button onClick={() => setBuilderOpen(true)} className="text-xs">
                  <Plus className="h-4 w-4" /> New order
                </Button>
              ) : null}
            </>
          }
        />

        {stats && <OpsPressureBar stats={stats} onDrill={(t) => goView(t)} />}

        <div className="ops-table-scroll flex gap-1 rounded-2xl border border-primary/10 bg-white p-1.5 ops-tower-tabs">
          {PRIMARY.filter((p) => !(wall && p.wallHide)).map(({ id, label, icon: Icon }) => {
            if (id === "tools") {
              return (
                <div key={id} className="relative">
                  <button
                    type="button"
                    onClick={() => {
                      if (view === "tools") {
                        setToolsOpen((o) => !o);
                      } else {
                        goView("tools", activeTool);
                      }
                    }}
                    className={cn(
                      "flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                      view === "tools"
                        ? "bg-secondary text-white"
                        : "text-primary/70 hover:bg-gray-bg"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                    <ChevronDown className="h-3.5 w-3.5 opacity-70" />
                  </button>
                  {toolsOpen && view === "tools" && (
                    <>
                      <div
                        className="fixed inset-0 z-20"
                        onClick={() => setToolsOpen(false)}
                        aria-hidden
                      />
                      <div className="absolute left-0 z-30 mt-1 min-w-[11rem] rounded-xl border border-primary/10 bg-white p-1 shadow-lg">
                        {TOOLS.map(({ id: tid, label: tlabel, icon: TIcon }) => (
                          <button
                            key={tid}
                            type="button"
                            onClick={() => {
                              setTool(tid);
                              setView("tools");
                              setToolsOpen(false);
                            }}
                            className={cn(
                              "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm",
                              activeTool === tid
                                ? "bg-secondary/10 font-medium text-secondary"
                                : "text-primary hover:bg-gray-bg"
                            )}
                          >
                            <TIcon className="h-4 w-4" />
                            {tlabel}
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              );
            }
            return (
              <button
                key={id}
                type="button"
                onClick={() => goView(id)}
                className={cn(
                  "flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                  view === id ? "bg-secondary text-white" : "text-primary/70 hover:bg-gray-bg"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            );
          })}
        </div>

        {view === "tools" && !wall && (
          <div className="flex flex-wrap gap-1">
            {TOOLS.map(({ id: tid, label: tlabel, icon: TIcon }) => (
              <button
                key={tid}
                type="button"
                onClick={() => setTool(tid)}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium",
                  activeTool === tid
                    ? "bg-secondary text-white"
                    : "border border-primary/10 text-primary/70 hover:bg-gray-bg"
                )}
              >
                <TIcon className="h-3.5 w-3.5" />
                {tlabel}
              </button>
            ))}
          </div>
        )}

        {view === "desk" && (
          <OpsDeskLayout
            tick={tick}
            stats={stats}
            onAssigned={refresh}
            onOpenOrder={openOrder}
            onOpenAttention={() => goView("attention")}
          />
        )}
        {view === "board" && <BoardPanel tick={tick} onMoved={refresh} onOpenOrder={openOrder} />}
        {view === "orders" && <OrdersTablePanel tick={tick} onOpenOrder={openOrder} />}
        {view === "attention" && <AttentionPanel tick={tick} onOpenOrder={openOrder} />}
        {view === "tools" && activeTool === "scheduled" && (
          <ScheduledBatchesPanel tick={tick} onOpenOrder={openOrder} />
        )}
        {view === "tools" && activeTool === "optimize" && (
          <OptimizePanel tick={tick} onOpenOrder={openOrder} onCommitted={refresh} />
        )}
        {view === "tools" && activeTool === "utilization" && <UtilizationPanel tick={tick} />}
        {view === "tools" && activeTool === "ai" && (
          <DispatcherCopilotPanel tick={tick} onOpenOrder={openOrder} onChanged={refresh} />
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
        <OpsCommandPalette onOpenOrder={openOrder} onJumpView={(v, t) => goView(v, t)} />
        <OpsAlertToast stats={stats} soundEnabled={sound} />
      </div>
    </AdminPage>
  );
}
