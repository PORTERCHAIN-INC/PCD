/** Idle session policy — shared across customer, merchant, driver, website, admin. */

export const INACTIVITY_TIMEOUT_MS = 45 * 60 * 1000;
export const INACTIVITY_CHECK_MS = 30_000;
export const INACTIVITY_ACTIVITY_THROTTLE_MS = 15_000;
export const INACTIVITY_STORAGE_KEY = "pc_last_activity_at";

export function readLastActivityAt(): number {
  if (typeof window === "undefined") return Date.now();
  try {
    const raw = window.localStorage.getItem(INACTIVITY_STORAGE_KEY);
    const n = raw ? Number(raw) : NaN;
    return Number.isFinite(n) ? n : Date.now();
  } catch {
    return Date.now();
  }
}

export function markActivity(at: number = Date.now()): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(INACTIVITY_STORAGE_KEY, String(at));
  } catch {
    /* private mode / quota — still rely on in-memory checks via callers */
  }
}

export function clearActivityMarker(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(INACTIVITY_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function isInactive(
  timeoutMs: number = INACTIVITY_TIMEOUT_MS,
  now: number = Date.now()
): boolean {
  return now - readLastActivityAt() >= timeoutMs;
}
