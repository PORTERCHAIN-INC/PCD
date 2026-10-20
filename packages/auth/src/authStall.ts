/**
 * Detects a Clerk sign-up/sign-in form whose Continue button stays busy forever.
 *
 * Production sign-up runs Clerk bot protection (Cloudflare Turnstile). When the challenge
 * cannot finish (reviewer VMs, privacy extensions, strict networks), Clerk never sends the
 * sign-up request and the button spins with no message — Shopify App Review saw exactly this.
 * The watchdog turns that silent hang into a visible, actionable notice.
 */

export const AUTH_STALL_TIMEOUT_MS = 20_000;

export type ButtonSnapshot = { disabled: boolean; loading: boolean };

/** Busy = Clerk marks the primary button loading/disabled while a request or CAPTCHA runs. */
export function isPrimaryButtonBusy(snapshot: ButtonSnapshot | null): boolean {
  return Boolean(snapshot && (snapshot.loading || snapshot.disabled));
}

/** Pure stall clock: returns the new busy-since timestamp and whether the form is stalled. */
export function nextStallState(
  busy: boolean,
  busySince: number | null,
  now: number,
  timeoutMs: number = AUTH_STALL_TIMEOUT_MS
): { busySince: number | null; stalled: boolean } {
  if (!busy) return { busySince: null, stalled: false };
  const since = busySince ?? now;
  return { busySince: since, stalled: now - since >= timeoutMs };
}
