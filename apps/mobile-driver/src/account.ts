/** Pure helpers for Profile, Pay & time and Availability (unit-tested; no React Native). */
import type { Schedule } from "./api";

const CODES: Record<string, string> = {
  required: "Required",
  invalid: "Check this",
  too_short: "Too short",
  too_long: "Too long",
  too_large: "Photo too large",
};

/** API 422 detail {field, code} (thrown as JSON text) -> a short inline message for that field. */
export function fieldError(e: unknown): { field: string; text: string } | null {
  const msg = e instanceof Error ? e.message : String(e ?? "");
  try {
    const d = JSON.parse(msg) as { field?: string; code?: string };
    if (d.field) return { field: d.field, text: CODES[d.code ?? ""] ?? "Check this" };
  } catch {
    /* not JSON */
  }
  return null;
}

export function hm(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
}

export const BLOCKS = {
  am: { start: "07:00", end: "13:00", label: "7–1" },
  day: { start: "08:00", end: "16:00", label: "8–4" },
  pm: { start: "12:00", end: "20:00", label: "12–8" },
  long: { start: "07:00", end: "19:00", label: "7–7" },
} as const;
export type BlockKey = keyof typeof BLOCKS;

export function blockOf(b?: { start: string; end: string }): BlockKey {
  const hit = (Object.keys(BLOCKS) as BlockKey[]).find(
    (k) => BLOCKS[k].start === b?.start && BLOCKS[k].end === b?.end
  );
  return hit ?? "day";
}

export function weeklyHours(s: Schedule): number {
  let m = 0;
  for (const blocks of Object.values(s))
    for (const b of blocks) {
      const [h1, m1] = b.start.split(":").map(Number);
      const [h2, m2] = b.end.split(":").map(Number);
      m += h2 * 60 + m2 - (h1 * 60 + m1);
    }
  return Math.round((m / 60) * 10) / 10;
}
