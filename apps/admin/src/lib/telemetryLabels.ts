/** Labels for GPS / ETA sources. A number without a source is a lie (Step 1 Wave 5). */

const ROAD_ETA = new Set(["valhalla", "osrm", "matrix", "routing"]);

export function formatSuggestionEta(
  minutes: number | null | undefined,
  source?: string | null
): string {
  if (minutes == null) {
    return source === "no_position" || source === "haversine" ? "No road ETA" : "—";
  }
  const rounded = `${Math.round(minutes)}m`;
  if (source && ROAD_ETA.has(source)) return `${rounded} road`;
  if (source === "haversine") return `${rounded} approx`;
  return rounded;
}

export function gpsSourceLabel(source: string | null | undefined): string {
  switch (source) {
    case "last_known":
      return "GPS: last-known (ingest)";
    case "fleetbase_mirror":
    case "fleetbase":
      return "GPS: Fleetbase mirror";
    case "mirror_miss":
      return "GPS: mirror miss";
    case "unavailable":
      return "GPS unavailable";
    default:
      return source ? `GPS: ${source.replace(/_/g, " ")}` : "GPS: unknown";
  }
}

export function gpsAgeLabel(
  recordedAt: string | null | undefined,
  nowMs = Date.now()
): string | null {
  if (!recordedAt) return null;
  const then = Date.parse(recordedAt);
  if (Number.isNaN(then)) return null;
  const sec = Math.max(0, Math.round((nowMs - then) / 1000));
  if (sec < 45) return `${sec}s ago`;
  if (sec < 3600) return `${Math.round(sec / 60)}m ago`;
  return `${Math.round(sec / 3600)}h ago`;
}

export function isStaleGps(recordedAt: string | null | undefined, nowMs = Date.now()): boolean {
  if (!recordedAt) return false;
  const then = Date.parse(recordedAt);
  if (Number.isNaN(then)) return false;
  return nowMs - then > 120_000;
}
