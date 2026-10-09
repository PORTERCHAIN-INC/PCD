/** Helpers for the super-admin checkout delivery-promise settings (cut-offs, waves, holidays). */

export type PromiseWave = { code: string; cutoff: string; start: string; end: string };
export type PromiseTier = {
  name: string;
  prefixes: string[];
  same_day: boolean;
  extra_days: number;
};

/** Python weekday numbers: Monday = 0 … Sunday = 6. */
export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;

/** EXAMPLE values waiting for an ops decision (mirrors the API placeholder list).
 * The wave (11:00 -> 14:00-21:00) and Mon-Sat days were approved on 2026-10-09. */
export const DELIVERY_PROMISE_PLACEHOLDERS: readonly string[] = ["holidays", "fsa_tiers"];

export const SERVICE_KINDS = [
  { key: "same_day", label: "Same day" },
  { key: "next_day", label: "Next day" },
  { key: "scheduled", label: "Later day" },
] as const;

const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function isHhmm(v: string): boolean {
  return HHMM.test(v.trim());
}

export function toggleWeekday(days: number[], day: number): number[] {
  const set = new Set(days);
  if (set.has(day)) set.delete(day);
  else set.add(day);
  return [...set].sort((a, b) => a - b);
}

/** One date per line (or comma separated). Returns valid ISO dates (sorted, unique) and the rest. */
export function parseHolidays(text: string): { dates: string[]; invalid: string[] } {
  const parts = text
    .split(/[\n,]+/)
    .map((p) => p.trim())
    .filter(Boolean);
  const dates = new Set<string>();
  const invalid: string[] = [];
  for (const p of parts) {
    if (ISO_DATE.test(p) && !Number.isNaN(Date.parse(`${p}T00:00:00Z`))) dates.add(p);
    else invalid.push(p);
  }
  return { dates: [...dates].sort(), invalid };
}

/** FSA prefixes like "L9, L0 K0A" -> ["L9", "L0", "K0A"]. */
export function parsePrefixes(text: string): string[] {
  const out = new Set<string>();
  for (const raw of text.split(/[\s,]+/)) {
    const p = raw
      .trim()
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, "");
    if (p && p.length <= 3) out.add(p);
  }
  return [...out];
}

export function waveProblems(waves: PromiseWave[]): string[] {
  const out: string[] = [];
  waves.forEach((w, i) => {
    const n = i + 1;
    if (!isHhmm(w.cutoff) || !isHhmm(w.start) || !isHhmm(w.end)) {
      out.push(`Wave ${n}: times must be HH:MM (24h).`);
    } else if (w.end <= w.start) {
      out.push(`Wave ${n}: window end must be after start.`);
    }
  });
  if (!waves.length) out.push("Add at least one wave.");
  return out;
}
