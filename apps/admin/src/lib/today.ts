/**
 * Ops "Today" — pure helpers for the single operations screen.
 * Merges the dispatch exception queue with the unassigned queue, ranks by risk
 * to the delivery promise, and derives the 4-number top strip.
 */
import type { DispatchExceptionItem, LiveEta } from "@/lib/dispatch";
import type { OpsStats, QueueOrder } from "@/lib/operations";

export type TodayFilter = "all" | "late" | "unassigned" | "failed";

export type TodayIssue = {
  key: string;
  order_id: string;
  order_number: string;
  kind: string;
  label: string;
  severity: DispatchExceptionItem["severity"];
  age_min: number | null;
  detail: string | null;
  /** One-click action this row offers. */
  action: "offer" | "fix" | "open";
  item?: DispatchExceptionItem;
};

export const SEVERITY_RANK: Record<DispatchExceptionItem["severity"], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const KIND_LABEL: Record<string, string> = {
  late: "Late",
  at_risk: "At risk",
  unassigned: "Unassigned",
  failed: "Failed delivery",
  damaged: "Damaged",
  lost: "Lost",
  return: "Return to sender",
  claim: "Claim open",
  margin: "Below margin",
  stuck: "Stuck",
  idle: "Driver idle",
  liftgate: "Needs liftgate",
};

export function issueLabel(i: Pick<DispatchExceptionItem, "kind" | "type">): string {
  if (i.kind === "exception") {
    if (i.type === "DRIVER_TIMEOUT") return "No driver accepted";
    if (i.type === "package_short_at_drop") return "Box missing at drop";
    if (i.type === "package_missing") return "Box missing at pickup";
    return i.type
      .toLowerCase()
      .replaceAll("_", " ")
      .replace(/^\w/, (c) => c.toUpperCase());
  }
  return KIND_LABEL[i.kind] ?? i.type;
}

export function issueBucket(
  i: Pick<TodayIssue, "kind" | "item">
): Exclude<TodayFilter, "all"> | null {
  if (i.kind === "late" || i.kind === "at_risk" || i.kind === "stuck") return "late";
  if (i.kind === "unassigned" || i.item?.type === "DRIVER_TIMEOUT") return "unassigned";
  if (["failed", "damaged", "lost", "return"].includes(i.kind)) return "failed";
  if (i.kind === "exception") return "failed";
  return null;
}

function waitMin(created: string | null | undefined, now: number): number | null {
  if (!created) return null;
  const t = new Date(created).getTime();
  return Number.isFinite(t) ? Math.max(0, Math.round((now - t) / 60000)) : null;
}

/** One queue, worst first: severity, then oldest. One row per order; unflagged unassigned orders join as medium/high. */
export function buildIssues(
  items: DispatchExceptionItem[],
  queue: QueueOrder[],
  now: number = Date.now()
): TodayIssue[] {
  const seen = new Set<string>();
  const out: TodayIssue[] = items.map((it) => {
    seen.add(it.order_id);
    const canOffer = it.kind === "unassigned" || it.type === "DRIVER_TIMEOUT";
    return {
      key: it.id,
      order_id: it.order_id,
      order_number: it.order_number,
      kind: it.kind,
      label: issueLabel(it),
      severity: it.severity,
      age_min: it.age_min,
      detail: it.fixes?.[0]?.why ?? null,
      action: it.fixes?.length ? "fix" : canOffer ? "offer" : "open",
      item: it,
    };
  });
  for (const q of queue) {
    if (seen.has(q.id) || q.driver_id) continue;
    const age = waitMin(q.created_at, now);
    out.push({
      key: `q:${q.id}`,
      order_id: q.id,
      order_number: q.order_number,
      kind: "unassigned",
      label: "Unassigned",
      severity: q.high_priority || (age ?? 0) >= 15 ? "high" : "medium",
      age_min: age,
      detail: [q.pickup, q.dropoff].filter(Boolean).join(" → ") || null,
      action: "offer",
    });
  }
  return out.sort(
    (a, b) =>
      SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] || (b.age_min ?? 0) - (a.age_min ?? 0)
  );
}

export function filterIssues(issues: TodayIssue[], f: TodayFilter): TodayIssue[] {
  return f === "all" ? issues : issues.filter((i) => issueBucket(i) === f);
}

export function filterCounts(issues: TodayIssue[]): Record<TodayFilter, number> {
  const c: Record<TodayFilter, number> = { all: issues.length, late: 0, unassigned: 0, failed: 0 };
  for (const i of issues) {
    const b = issueBucket(i);
    if (b) c[b] += 1;
  }
  return c;
}

export type TodayKpis = {
  onTimePct: number | null;
  unassigned: number;
  atRisk: number;
  done: number;
  total: number;
};

/** The only four numbers on the screen. Live ETAs win over day stats when present. */
export function kpis(stats: OpsStats | null, etas: LiveEta[], issues: TodayIssue[]): TodayKpis {
  const judged = etas.filter((e) => e.status !== "unknown");
  const ok = judged.filter((e) => e.status === "on_time").length;
  const unassigned = filterCounts(issues).unassigned;
  return {
    onTimePct: judged.length ? Math.round((ok / judged.length) * 100) : null,
    unassigned: Math.max(unassigned, stats?.waiting_dispatch ?? 0),
    atRisk:
      etas.filter((e) => e.status === "at_risk" || e.status === "late").length ||
      (stats?.sla_at_risk ?? 0) + (stats?.sla_breached ?? 0),
    done: stats?.completed_today ?? 0,
    total: stats?.orders_today ?? 0,
  };
}

export type TimelineStep = { label: string; at: string | null; done: boolean };

const STEPS: [string, string[]][] = [
  ["Created", ["created", "pending", "booked", "confirmed"]],
  ["Assigned", ["assigned", "driver_assigned", "accepted", "dispatched"]],
  ["Picked up", ["picked_up", "pickup_complete", "in_transit", "out_for_delivery"]],
  ["Delivered", ["delivered", "completed"]],
];

const pick = (r: Record<string, unknown>, keys: string[]) => {
  for (const k of keys) if (typeof r[k] === "string" && r[k]) return r[k] as string;
  return null;
};

/** Collapse any order timeline payload into the 4-step promise timeline. */
export function promiseTimeline(
  state: string,
  timeline: Record<string, unknown>[]
): TimelineStep[] {
  const events = timeline.map((r) => ({
    key: (pick(r, ["status", "state", "event_type", "event", "type", "label"]) ?? "")
      .toLowerCase()
      .replace(/^order[._]/, "")
      .replaceAll(" ", "_"),
    at: pick(r, ["at", "occurred_at", "created_at", "timestamp", "time"]),
  }));
  const s = state.toLowerCase();
  const reached = STEPS.findIndex(([, keys]) => keys.includes(s));
  return STEPS.map(([label, keys], idx) => {
    const ev = events.find((e) => keys.some((k) => e.key.includes(k)));
    return { label, at: ev?.at ?? null, done: !!ev || (reached >= 0 && idx <= reached) };
  });
}

export function ago(ms: number | null, now: number = Date.now()): string {
  if (!ms) return "—";
  const s = Math.max(0, Math.round((now - ms) / 1000));
  if (s < 10) return "live";
  if (s < 60) return `${s}s ago`;
  return `${Math.round(s / 60)}m ago`;
}

export type Pos = { id: string; lat: number; lng: number };

/** Ease-out cubic: fast start, gentle arrival — reads as a vehicle settling, not a jump. */
export const easeOut = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

/** Jumps larger than this (~2 km) snap instead of gliding — a teleporting van across town is worse. */
const MAX_GLIDE_DEG = 0.02;

/**
 * Interpolate driver positions between two polls. New drivers appear at their target,
 * vanished drivers drop out, and big jumps snap.
 */
export function glide<T extends Pos>(from: Pos[], to: T[], t: number): T[] {
  const prev = new Map(from.map((p) => [p.id, p]));
  const k = easeOut(t);
  return to.map((p) => {
    const a = prev.get(p.id);
    if (!a) return p;
    const far = Math.abs(p.lat - a.lat) > MAX_GLIDE_DEG || Math.abs(p.lng - a.lng) > MAX_GLIDE_DEG;
    if (far || k >= 1) return p;
    return { ...p, lat: a.lat + (p.lat - a.lat) * k, lng: a.lng + (p.lng - a.lng) * k };
  });
}

export type LiveMsg =
  | { type: "hello" | "pong" }
  | { type: "driver"; id: string; lat: number; lng: number; heading?: number | null; at?: string }
  | { type: "order"; id: string; event: string; state?: string | null }
  | { type: "exception"; id: string; event: string; order_id?: string | null };

/**
 * Apply one live GPS fix to the cached map snapshot. Only drivers already on the board move:
 * the snapshot is the consent/shift filter, so a fix never reveals someone the board hides.
 * Out-of-order fixes (older `at`) are ignored.
 */
export function applyDriverFix<
  S extends { drivers: { id: string; lat: number; lng: number; recorded_at?: string | null }[] },
>(snap: S | null | undefined, fix: Extract<LiveMsg, { type: "driver" }>): S | null | undefined {
  if (!snap) return snap;
  const i = snap.drivers.findIndex((d) => d.id === fix.id);
  if (i < 0) return snap;
  const cur = snap.drivers[i];
  if (fix.at && cur.recorded_at && Date.parse(fix.at) < Date.parse(cur.recorded_at)) return snap;
  const drivers = snap.drivers.slice();
  drivers[i] = { ...cur, lat: fix.lat, lng: fix.lng, recorded_at: fix.at ?? cur.recorded_at };
  return { ...snap, drivers };
}

/** Which cached Today queries a live event makes stale (driver fixes patch the map in place). */
export function staleKeysFor(msg: LiveMsg): string[] {
  if (msg.type === "order")
    return [
      "today-stats",
      "today-queue",
      "today-eta",
      "today-exceptions",
      "today-map",
      "today-order",
    ];
  if (msg.type === "exception") return ["today-exceptions", "today-stats", "today-order"];
  return [];
}
