import { adminFetch } from "@/lib/api";

export type MetricsBaseline = {
  route: Record<string, number | string>;
  year: Record<string, number>;
  break_even_stops_per_day: Record<string, number>;
  payback_months: Record<string, number>;
  kingman: Record<string, number>;
  utilisation_thresholds: { yellow: number; red: number };
  compliance_money: Record<string, number | string>;
};

export const metrics = {
  baseline: (t: string, stopsPerDay = 20) =>
    adminFetch<MetricsBaseline>(
      `/v1/admin/metrics/baseline?stops_per_day=${encodeURIComponent(stopsPerDay)}`,
      t
    ),
};

export function fmtMetric(key: string, v: number | string): string {
  if (typeof v === "string") return v;
  if (/roic|roa|wacc|margin|rate|ratio/.test(key)) return `${(v * 100).toFixed(1)}%`;
  return Math.abs(v) >= 100
    ? `$${v.toLocaleString("en-CA", { maximumFractionDigits: 0 })}`
    : v.toFixed(2);
}
