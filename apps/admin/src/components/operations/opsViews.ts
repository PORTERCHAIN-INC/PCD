import type { OpsStats } from "@/lib/operations";

/** Primary Control Tower views (Desk-first IA). */
export type OpsViewId = "desk" | "board" | "orders" | "attention" | "tools";

/** Secondary tools demoted under Tools. */
export type OpsToolId = "scheduled" | "optimize" | "utilization" | "ai";

export type OpsDrillTarget = OpsViewId | OpsToolId;

const VIEWS = new Set<string>(["desk", "board", "orders", "attention", "tools"]);
const TOOLS = new Set<string>(["scheduled", "optimize", "utilization", "ai"]);

/** Legacy 12-tab ids → new view (+ optional tool). */
const LEGACY: Record<string, { view: OpsViewId; tool?: OpsToolId }> = {
  overview: { view: "desk" },
  map: { view: "desk" },
  queue: { view: "desk" },
  activity: { view: "desk" },
  board: { view: "board" },
  orders: { view: "orders" },
  exceptions: { view: "attention" },
  sla: { view: "attention" },
  scheduled: { view: "tools", tool: "scheduled" },
  optimize: { view: "tools", tool: "optimize" },
  utilization: { view: "tools", tool: "utilization" },
  ai: { view: "tools", tool: "ai" },
  copilot: { view: "tools", tool: "ai" },
};

export function parseOpsSearchParams(sp: URLSearchParams): {
  view: OpsViewId;
  tool: OpsToolId | null;
} {
  const rawView = sp.get("view") ?? "";
  const rawTool = sp.get("tool") ?? "";

  if (VIEWS.has(rawView)) {
    const view = rawView as OpsViewId;
    if (view === "tools" && TOOLS.has(rawTool)) {
      return { view, tool: rawTool as OpsToolId };
    }
    return { view, tool: view === "tools" ? "optimize" : null };
  }

  const legacy = LEGACY[rawView] ?? (rawTool ? LEGACY[rawTool] : undefined);
  if (legacy) {
    return { view: legacy.view, tool: legacy.tool ?? null };
  }

  return { view: "desk", tool: null };
}

export function writeOpsSearchParams(view: OpsViewId, tool: OpsToolId | null): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  url.searchParams.set("view", view);
  if (view === "tools" && tool) {
    url.searchParams.set("tool", tool);
  } else {
    url.searchParams.delete("tool");
  }
  window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

export function pressureCounts(stats: OpsStats | null | undefined): {
  waiting: number;
  delayed: number;
  sla: number;
  exceptions: number;
  hasPressure: boolean;
} {
  const waiting = stats?.waiting_dispatch ?? 0;
  const delayed = stats?.delayed_orders ?? 0;
  const sla = (stats?.sla_at_risk ?? 0) + (stats?.sla_breached ?? 0);
  const exceptions = stats?.open_exceptions ?? 0;
  return {
    waiting,
    delayed,
    sla,
    exceptions,
    hasPressure: waiting > 0 || delayed > 0 || sla > 0 || exceptions > 0,
  };
}
