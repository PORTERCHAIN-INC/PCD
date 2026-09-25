"use client";

import { useEffect, useRef, useState } from "react";
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
import { useApiData } from "@/hooks/useApiData";
import { ops } from "@/lib/operations";
import { OpsPressureBar } from "@/components/operations/OpsPressureBar";
import { PushHealthStrip } from "@/components/operations/PushHealthStrip";
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
import { Button, Spinner } from "@/components/crm/primitives";
import dynamic from "next/dynamic";

const Order360Drawer = dynamic(
  () => import("@/components/orders/Order360Drawer").then((m) => ({ default: m.Order360Drawer })),
  { loading: () => null, ssr: false }
);
const OrderBuilderModal = dynamic(
  () =>
    import("@/components/orders/OrderBuilderModal").then((m) => ({
      default: m.OrderBuilderModal,
    })),
  { loading: () => <Spinner />, ssr: false }
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
  const [updatedAt, setUpdatedAt] = useState<Date>(new Date());
  const [drawerOrderId, setDrawerOrderId] = useState<string | null>(null);
  const [builderOpen, setBuilderOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const urlSyncReady = useRef(false);

  useEffect(() => {
    const raw = localStorage.getItem(DISPLAY_KEY);
    if (raw === "dark" || raw === "wall" || raw === "default") setDisplay(raw);
    urlSyncReady.current = true;
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
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-primary">
              <Radio className="h-5 w-5 text-secondary" /> Operations Control Tower
            </h1>
            {!wall && (
              <p className="text-sm text-muted">
                Dispatch desk — assign waiting work, clear exceptions, watch the network.
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <PushHealthStrip tick={tick} compactWhenOk />
            <span className="flex items-center gap-1.5 text-xs text-muted">
              <Clock className="h-3.5 w-3.5" /> Updated {updatedAt.toLocaleTimeString("en-CA")}
              {auto && <span className="text-muted/70">· every {Math.round(pollMs / 1000)}s</span>}
            </span>
            <Button
              variant="outline"
              onClick={cycleDisplay}
              className="text-xs"
              title="Display mode"
            >
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
            {!wall && (
              <Button onClick={() => setBuilderOpen(true)} className="text-xs">
                <Plus className="h-4 w-4" /> New order
              </Button>
            )}
          </div>
        </div>

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
