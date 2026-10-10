"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { Keyboard, MoreHorizontal, Plus, RefreshCw, Route } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { PageSkeleton } from "@porterchain/ui/loading";
import AdminPage from "@/components/layout/AdminPage";
import { Order360Drawer } from "@/components/orders/Order360Drawer";
import { OpsCommandPalette } from "@/components/operations/OpsCommandPalette";
import { FleetPlanPanel } from "@/components/dispatch/FleetPlanPanel";
import { PartnersPanel } from "@/components/dispatch/PartnersPanel";
import { PartnerJobsPanel } from "@/components/dispatch/PartnerJobsPanel";
import { RetentionCard } from "@/components/dispatch/RetentionCard";
import { ScheduledBatchesPanel } from "@/components/operations/ScheduledBatchesPanel";
import { UtilizationPanel } from "@/components/operations/UtilizationPanel";
import { BoardPanel } from "@/components/operations/BoardPanel";
import { PushHealthStrip } from "@/components/operations/PushHealthStrip";
import { MetricsBar } from "@/components/dispatch/MetricsBar";
import { TodayPanel } from "@/components/dispatch/TodayPanel";
import { ExceptionsQueue } from "@/components/dispatch/ExceptionsQueue";
import { LiveEtaList } from "@/components/dispatch/LiveEtaList";
import { FleetCapacityEditor } from "@/components/dispatch/FleetCapacityEditor";
import { useApiData } from "@/hooks/useApiData";
import { dispatch, type DispatchView } from "@/lib/dispatch";
import {
  FLEET_SECTIONS,
  type FleetSection,
  isTypingTarget,
  shortcutFor,
} from "@/lib/dispatch-shortcuts";

const LiveMapPanel = dynamic(
  () => import("@/components/operations/LiveMapPanel").then((m) => ({ default: m.LiveMapPanel })),
  { loading: () => <PageSkeleton rows={3} />, ssr: false }
);
const OrderBuilderModal = dynamic(
  () =>
    import("@/components/orders/OrderBuilderModal").then((m) => ({ default: m.OrderBuilderModal })),
  { loading: () => <PageSkeleton rows={3} />, ssr: false }
);
const DriversListClient = dynamic(() => import("@/components/drivers/DriversListClient"), {
  loading: () => <PageSkeleton rows={4} />,
  ssr: false,
});

const TABS: { id: DispatchView | "orders"; label: string; href: string }[] = [
  { id: "today", label: "Today", href: "/dispatch/today" },
  { id: "plan", label: "Plan", href: "/dispatch/plan" },
  { id: "live", label: "Live", href: "/dispatch/live" },
  { id: "exceptions", label: "Exceptions", href: "/dispatch/exceptions" },
  { id: "fleet", label: "Fleet", href: "/dispatch/fleet" },
];

const SUBTITLE: Record<DispatchView, string> = {
  today: "Give every waiting order a driver.",
  plan: "Build the day: sequence stops, check fill, commit.",
  live: "Where every delivery is, and whether it lands on time.",
  exceptions: "Everything that needs a human, worst first.",
  fleet: "Drivers, vehicles and how much each can carry.",
};

const POLL_MS = 30_000;

export function DispatchShell({ view }: { view: DispatchView }) {
  const router = useRouter();
  const [tick, setTick] = useState(0);
  const [drawerOrderId, setDrawerOrderId] = useState<string | null>(null);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [days, setDays] = useState(7);
  const [menu, setMenu] = useState(false);
  const [help, setHelp] = useState(false);
  const [fleetSection, setFleetSection] = useState<FleetSection>("drivers");
  const { data: exc } = useApiData((t) => dispatch.exceptions(t), [tick], {
    key: "dispatch-exceptions",
  });
  const excTotal = exc?.total ?? 0;

  // Dispatcher keyboard: 1–7 tabs · P plan · N new order · R refresh · ? help · Esc close.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTypingTarget(e.target)) return;
      const action = shortcutFor(e.key);
      if (!action) return;
      if (action.kind !== "close") e.preventDefault();
      if (action.kind === "tab") router.push(TABS[action.index].href);
      else if (action.kind === "plan") {
        const btn = document.querySelector<HTMLButtonElement>('[data-dispatch-shortcut="plan"]');
        if (btn && !btn.disabled) btn.click();
        else router.push("/dispatch/plan");
      } else if (action.kind === "approve") {
        const btn = document.querySelector<HTMLButtonElement>('[data-dispatch-shortcut="approve"]');
        if (btn && !btn.disabled) btn.click();
      } else if (action.kind === "new") setBuilderOpen(true);
      else if (action.kind === "refresh") setTick((x) => x + 1);
      else if (action.kind === "help") setHelp((h) => !h);
      else if (action.kind === "close") {
        setHelp(false);
        setMenu(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  useEffect(() => {
    const id = setInterval(() => setTick((x) => x + 1), POLL_MS);
    return () => clearInterval(id);
  }, []);

  const refresh = () => setTick((x) => x + 1);
  const openOrder = (id: string) => setDrawerOrderId(id);
  const title = TABS.find((t) => t.id === view)?.label ?? "Dispatch";

  return (
    <AdminPage className="dispatch !space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-secondary">
            Dispatch
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-primary">{title}</h1>
          <p className="text-sm text-muted">{SUBTITLE[view]}</p>
        </div>
        <div className="flex w-full items-center gap-2 sm:w-auto">
          <div className="relative">
            <button
              type="button"
              aria-label="More actions"
              aria-expanded={menu}
              onClick={() => setMenu((m) => !m)}
              className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-primary/15 bg-white text-primary"
            >
              <MoreHorizontal className="h-5 w-5" aria-hidden />
            </button>
            {menu && (
              <div
                role="menu"
                className="absolute left-0 z-30 mt-1 w-56 rounded-xl border border-primary/10 bg-white p-1 shadow-xl sm:left-auto sm:right-0"
              >
                {[
                  { label: "New order", key: "N", icon: Plus, run: () => setBuilderOpen(true) },
                  { label: "Refresh", key: "R", icon: RefreshCw, run: refresh },
                  {
                    label: "Keyboard shortcuts",
                    key: "?",
                    icon: Keyboard,
                    run: () => setHelp(true),
                  },
                ].map((m) => (
                  <button
                    key={m.label}
                    role="menuitem"
                    type="button"
                    onClick={() => {
                      setMenu(false);
                      m.run();
                    }}
                    className="flex min-h-10 w-full items-center gap-2 rounded-lg px-3 text-left text-sm text-primary hover:bg-primary/5"
                  >
                    <m.icon className="h-4 w-4" aria-hidden />
                    <span className="flex-1">{m.label}</span>
                    <kbd className="rounded border border-primary/15 px-1.5 text-[11px] text-muted">
                      {m.key}
                    </kbd>
                  </button>
                ))}
              </div>
            )}
          </div>
          {/* One main action per screen: other views own their action (Apply, Commit, Save); P still plans. */}
          {view === "today" && (
            <Link
              href="/dispatch/plan"
              aria-keyshortcuts="P"
              className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold text-white shadow-sm sm:flex-none"
              style={{ backgroundColor: "var(--primary)" }}
            >
              <Route className="h-4 w-4" />
              Plan the day
            </Link>
          )}
        </div>
      </header>

      <nav aria-label="Dispatch sections" className="-mx-1 overflow-x-auto">
        <ul className="flex min-w-max gap-1 px-1">
          {TABS.map((t, i) => (
            <li key={t.id}>
              <Link
                href={t.href}
                title={`${t.label} (${i + 1})`}
                aria-keyshortcuts={String(i + 1)}
                aria-current={t.id === view ? "page" : undefined}
                className={cn(
                  "inline-flex min-h-10 items-center rounded-full px-4 text-sm font-medium transition-colors",
                  t.id === view ? "text-white" : "text-primary/75 hover:bg-primary/5"
                )}
                style={t.id === view ? { backgroundColor: "var(--primary)" } : undefined}
              >
                {t.label}
                {t.id === "exceptions" && excTotal > 0 && (
                  <span
                    className={cn(
                      "ml-1.5 rounded-full px-1.5 text-xs font-bold tabular-nums",
                      t.id === view ? "bg-white text-primary" : "bg-red-600 text-white"
                    )}
                  >
                    {excTotal}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {view === "today" && (
        <div className="space-y-2">
          <div className="flex justify-end gap-1" role="group" aria-label="Metrics window">
            {[1, 7, 30].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDays(d)}
                aria-pressed={days === d}
                className={cn(
                  "min-h-8 rounded-full px-3 text-xs font-medium",
                  days === d ? "bg-secondary text-white" : "border border-primary/15 text-primary"
                )}
              >
                {d === 1 ? "Today" : `${d}d`}
              </button>
            ))}
          </div>
          <MetricsBar tick={tick} days={days} />
        </div>
      )}

      {view === "today" && (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <TodayPanel tick={tick} onOpenOrder={openOrder} onChanged={refresh} />
          <BoardPanel tick={tick} onMoved={refresh} onOpenOrder={openOrder} />
        </div>
      )}

      {view === "plan" && (
        <div className="space-y-4">
          <FleetPlanPanel tick={tick} onOpenOrder={openOrder} onCommitted={refresh} />
          <ScheduledBatchesPanel tick={tick} onOpenOrder={openOrder} />
        </div>
      )}

      {view === "live" && (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <LiveMapPanel tick={tick} onOpenOrder={openOrder} />
          <LiveEtaList tick={tick} onOpenOrder={openOrder} />
        </div>
      )}

      {view === "exceptions" && (
        <ExceptionsQueue tick={tick} onOpenOrder={openOrder} onChanged={refresh} />
      )}

      {view === "fleet" && (
        <div className="space-y-4">
          <div
            className="inline-flex rounded-full border border-primary/10 bg-white p-1"
            role="tablist"
            aria-label="Fleet"
          >
            {FLEET_SECTIONS.map((f) => (
              <button
                key={f.id}
                type="button"
                role="tab"
                aria-selected={fleetSection === f.id}
                onClick={() => setFleetSection(f.id)}
                className={cn(
                  "min-h-10 rounded-full px-4 text-sm font-medium",
                  fleetSection === f.id ? "text-white" : "text-primary/75 hover:bg-primary/5"
                )}
                style={fleetSection === f.id ? { backgroundColor: "var(--primary)" } : undefined}
              >
                {f.label}
              </button>
            ))}
          </div>
          {fleetSection === "drivers" && (
            <>
              <PushHealthStrip tick={tick} compactWhenOk />
              <UtilizationPanel tick={tick} />
              <DriversListClient />
            </>
          )}
          {fleetSection === "vehicles" && <FleetCapacityEditor tick={tick} />}
          {fleetSection === "partners" && (
            <>
              <PartnerJobsPanel tick={tick} />
              <PartnersPanel tick={tick} />
            </>
          )}
          {fleetSection === "data" && <RetentionCard tick={tick} />}
        </div>
      )}

      {help && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Keyboard shortcuts"
          className="fixed inset-0 z-50 flex items-center justify-center bg-primary/40 p-4"
          onClick={() => setHelp(false)}
        >
          <div
            className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-lg font-bold text-primary">Keyboard</p>
            <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              {[
                [`1 – ${TABS.length}`, TABS.map((t) => t.label).join(" · ")],
                ["P", "Plan the day"],
                ["A", "Approve the draft plan"],
                ["N", "New order"],
                ["R", "Refresh"],
                ["⌘K", "Search orders & jump"],
                ["?", "This sheet"],
                ["Esc", "Close"],
              ].map(([k, v]) => (
                <div key={k} className="contents">
                  <dt>
                    <kbd className="rounded-md border border-primary/15 bg-primary/[0.03] px-2 py-0.5 font-mono text-xs text-primary">
                      {k}
                    </kbd>
                  </dt>
                  <dd className="text-primary/80">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
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
      <OpsCommandPalette onOpenOrder={openOrder} onJumpView={(href) => router.push(href)} />
    </AdminPage>
  );
}
