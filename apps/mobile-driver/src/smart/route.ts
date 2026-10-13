/**
 * Pure route smarts (no network, no paid APIs): van load order, end-of-day summary,
 * customer heads-up text, battery-saver GPS mode, and smart warnings.
 */
import { isPickup, type DispatchRoute, type DispatchStop } from "../dispatchRoute";

/**
 * Load the van last-out-first-in: the last delivery goes in first (back of the van), the next
 * delivery goes in last (by the door). Returns deliveries still to do, in loading order.
 */
export function loadOrder(route: DispatchRoute | null): { stop: DispatchStop; position: number }[] {
  if (!route) return [];
  const todo = route.stops
    .map((stop, i) => ({ stop, position: i + 1 }))
    .filter(
      ({ stop }) => !isPickup(stop.kind) && stop.status !== "done" && stop.status !== "failed"
    );
  return todo.reverse();
}

export type DaySummary = {
  total: number;
  done: number;
  failed: number;
  pickups: number;
  drops: number;
  boxes: number;
  proofs: number;
  onTimePct: number | null;
};

export function daySummary(route: DispatchRoute | null): DaySummary {
  const stops = route?.stops ?? [];
  const done = stops.filter((s) => s.status === "done");
  return {
    total: stops.length,
    done: done.length,
    failed: stops.filter((s) => s.status === "failed").length,
    pickups: done.filter((s) => isPickup(s.kind)).length,
    drops: done.filter((s) => !isPickup(s.kind)).length,
    boxes: done.reduce((n, s) => n + (s.boxes || 0), 0),
    proofs: done.filter((s) => s.needs_pod).length,
    onTimePct: null, // route has no time windows yet (deferred: late-risk warning)
  };
}

/** Prefilled SMS so the driver never types while driving. */
export function headsUpText(etaMinutes: number | null, kind: DispatchStop["kind"]): string {
  const what = isPickup(kind) ? "pick up your order" : "deliver your order";
  if (etaMinutes == null) return `Hi, this is your PorterChain driver. I'm on my way to ${what}.`;
  const m = Math.max(1, Math.round(etaMinutes));
  return `Hi, this is your PorterChain driver. I'll be there to ${what} in about ${m} min.`;
}

/** Battery saver: below the Settings threshold (default 20 %) or OS low-power mode, GPS drops to balanced accuracy. */
export function gpsMode(
  level: number | null,
  lowPower: boolean,
  thresholdPct = 20
): "high" | "saver" {
  if (lowPower) return "saver";
  if (thresholdPct > 0 && level != null && level >= 0 && level < thresholdPct / 100) return "saver";
  return "high";
}

export type Warning = { id: string; tone: "warn" | "danger" | "info"; text: string };

/** Glanceable warnings shown above the stop (max 2; most urgent first). */
export function stopWarnings(input: {
  stop: DispatchStop | null;
  fixAgeMs: number | null;
  accuracyM: number | null;
  battery: number | null;
  offline: boolean;
  speedMps: number | null;
}): Warning[] {
  const w: Warning[] = [];
  const { stop } = input;
  if (input.battery != null && input.battery >= 0 && input.battery < 0.15)
    w.push({
      id: "battery",
      tone: "danger",
      text: `Battery ${Math.round(input.battery * 100)}% · plug in`,
    });
  if (input.offline)
    w.push({ id: "offline", tone: "warn", text: "No signal · actions save on this phone" });
  else if (input.fixAgeMs != null && input.fixAgeMs > 120_000)
    w.push({ id: "gps", tone: "warn", text: "GPS lost · check-in may need a tap" });
  else if (input.accuracyM != null && input.accuracyM > 80)
    w.push({ id: "gps-weak", tone: "info", text: "Weak GPS · auto-arrive paused" });
  if (stop?.liftgate)
    w.push({ id: "liftgate", tone: "warn", text: "Liftgate needed at this stop" });
  if (stop && (stop.lat == null || stop.lng == null))
    w.push({ id: "noloc", tone: "info", text: "No map pin · navigate by address" });
  return w.slice(0, 2);
}
