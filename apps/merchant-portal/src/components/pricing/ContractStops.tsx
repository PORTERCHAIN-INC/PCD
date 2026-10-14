"use client";

/** Per-stop explanation of a contract quote: address tier, parcels, boxes, weight, handling. */
type ParcelDetail = {
  boxes?: number;
  combined_weight_kg?: number | null;
  combined_dimensions_cm?: number[] | null;
  combined_volume_m3?: number | null;
  handling_tier?: string;
  handling_cents?: number;
};
type StopRow = {
  stop: number;
  fsa: string;
  tier: string;
  stop_rate_cents?: number;
  parcels: number;
  boxes?: number;
  billable_stops: number;
  stop_cents: number;
  handling_cents: number;
  combined_weight_kg?: number | null;
  parcel_detail?: ParcelDetail[];
};
type LiftFlag = { stop: number; note: string };

const TIER_LABEL: Record<string, string> = {
  standard: "Standard",
  handling_1: "Heavy Tier 1",
  handling_2: "Heavy Tier 2",
  handling_3: "Heavy Tier 3 (over Tier 2 + $50)",
};

const money = (c: number) => `$${(c / 100).toFixed(2)}`;
const cm = (d?: number[] | null) =>
  d && d.length === 3 ? `${d.map((x) => Math.round(x / 2.54)).join(" × ")} in` : null;

export default function ContractStops({ metadata }: { metadata?: Record<string, unknown> | null }) {
  const rows = (metadata?.contract_stops as StopRow[] | undefined) ?? [];
  const flags = (metadata?.lift_flags as LiftFlag[] | undefined) ?? [];
  if (!rows.length) return null;
  const top = Number(metadata?.route_minimum_top_up_cents ?? 0);
  return (
    <div className="space-y-2 rounded-xl bg-gray-bg p-3 text-xs" data-testid="contract-stops">
      {rows.map((r) => (
        <div key={r.stop}>
          <p className="font-medium text-primary">
            Stop {r.stop} · {r.fsa} · {r.tier}
            {r.stop_rate_cents ? ` (${money(r.stop_rate_cents)}/stop)` : ""} — {r.parcels} parcel
            {r.parcels === 1 ? "" : "s"}, {r.boxes ?? r.parcels} box
            {(r.boxes ?? r.parcels) === 1 ? "" : "es"}
            {r.billable_stops !== 1 ? ` → ${r.billable_stops} billable stops` : " → 1 stop"}
          </p>
          <ul className="ml-3 list-disc text-gray-700">
            {(r.parcel_detail ?? []).map((p, i) => (
              <li key={i}>
                Parcel {i + 1}: {p.boxes ?? 1} box{(p.boxes ?? 1) === 1 ? "" : "es"}
                {p.combined_weight_kg ? ` · ${p.combined_weight_kg} kg total` : ""}
                {cm(p.combined_dimensions_cm) ? ` · ${cm(p.combined_dimensions_cm)} stacked` : ""}
                {p.combined_volume_m3 ? ` · ${p.combined_volume_m3} m³` : ""} ·{" "}
                {TIER_LABEL[p.handling_tier ?? "standard"] ?? p.handling_tier}
                {p.handling_cents ? ` +${money(p.handling_cents)}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ))}
      {top > 0 && (
        <p className="text-gray-700">
          Below the {String(metadata?.fsa_tier ?? "")} route minimum (
          {money(Number(metadata?.route_minimum_cents ?? 0))}): top-up {money(top)}.
        </p>
      )}
      {flags.map((f) => (
        <p key={f.stop} className="text-amber-800">
          {f.note}
        </p>
      ))}
      <p className="text-muted">HST extra. The price is locked when you book.</p>
    </div>
  );
}
