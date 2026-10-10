"use client";

export type TrackingEta = {
  source?: string;
  duration_seconds?: number;
  distance_meters?: number;
  polyline?: string;
  arrives_at?: string;
  label?: string;
};

export function formatEta(seconds?: number): string {
  if (!seconds) return "—";
  if (seconds < 60) return "< 1 min";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

/** A number without a source is a lie (Step 1 Wave 6) — said in customer words, no engine names. */
export function etaSourceLabel(source?: string | null): string | null {
  switch (source) {
    case "osrm":
      return "Live road ETA";
    case "valhalla":
      return "Road ETA";
    case "matrix":
    case "routing":
      return "Road network";
    case "scheduled":
      return "Scheduled window";
    case "haversine":
      return "Approximate";
    default:
      return null;
  }
}

function formatArrival(iso?: string): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString(undefined, {
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export type TrackEtaPanelProps = {
  eta?: TrackingEta | null;
  delivered?: boolean;
  className?: string;
  title?: string;
  arrivalPrefix?: string;
  distanceSuffix?: string;
};

export function TrackEtaPanel({
  eta,
  delivered = false,
  className = "",
  title = "Estimated arrival",
  arrivalPrefix = "Arrives",
  distanceSuffix = "km remaining",
}: TrackEtaPanelProps) {
  if (delivered) {
    return (
      <div
        className={`rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 ${className}`.trim()}
      >
        <p className="text-xs font-medium uppercase tracking-wide text-emerald-800">{title}</p>
        <p className="mt-1 text-lg font-semibold text-emerald-950">Delivered</p>
      </div>
    );
  }

  if (!eta) return null;

  const source = eta.source ?? null;
  const sourceCaption = etaSourceLabel(source);
  const isApprox = source === "haversine";
  const label = isApprox ? "No road ETA" : (eta.label ?? formatEta(eta.duration_seconds));
  const arrival = formatArrival(eta.arrives_at);
  const distanceKm =
    typeof eta.distance_meters === "number" ? (eta.distance_meters / 1000).toFixed(1) : null;

  return (
    <div
      className={`rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 ${className}`.trim()}
      data-testid="track-eta-panel"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-sky-900">{title}</p>
      <p className="mt-1 text-2xl font-bold text-sky-950">{label}</p>
      {sourceCaption && <p className="mt-0.5 text-xs text-sky-800">{sourceCaption}</p>}
      {arrival && !isApprox && (
        <p className="mt-1 text-sm text-sky-800">
          {arrivalPrefix} {arrival}
        </p>
      )}
      {distanceKm && (
        <p className="mt-1 text-xs text-sky-700">
          {distanceKm} {isApprox ? "km approx" : distanceSuffix}
        </p>
      )}
    </div>
  );
}
