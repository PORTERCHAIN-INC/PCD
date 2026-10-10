/** Driver-facing labels for next-stop / mileage / optimize (Step 1 Wave 5). */

const ROAD = new Set(["valhalla", "osrm", "matrix", "routing"]);

export function formatNextStopMeta(opts: {
  eta?: number | null;
  distance?: number | null;
  source?: string | null;
}): string {
  const parts: string[] = [];
  const src = opts.source ?? "";
  const roadish =
    ROAD.has(src) || src.includes("valhalla") || src.includes("osrm") || src.includes("matrix");
  if (opts.eta != null) {
    parts.push(roadish ? `~${opts.eta} min (road)` : `~${opts.eta} min`);
  } else if (src === "haversine") {
    parts.push("distance only — not a road ETA");
  } else if (src.startsWith("day_plan") || src.startsWith("sequence")) {
    parts.push("Day plan");
  }
  if (opts.distance != null) {
    const km = `${(opts.distance / 1000).toFixed(1)} km`;
    parts.push(src === "haversine" ? `${km} approx` : km);
  }
  return parts.join(" · ");
}

export function mileageCaption(source?: string | null): string {
  if (source === "last_known_haversine") return "Approximate GPS path (not odometer)";
  if (source === "stored") return "Last stored shift total";
  return "From GPS during this shift";
}

export function optimizeEngineNote(engine?: string | null): string {
  if (engine === "haversine") return "";
  if (
    engine === "porterchain" ||
    engine === "ortools" ||
    engine === "vroom" ||
    engine === "greedy" ||
    engine === "insertion"
  ) {
    return "Day plan";
  }
  if (engine === "valhalla" || engine === "osrm") return "road network";
  return "";
}
