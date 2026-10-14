/**
 * Which server answers mean "this saved action is wrong" (park it, tell the driver) vs
 * "try again later" (keep it queued). Auth/permission answers are about the session, not
 * the action: a token refresh or a server-side permission blip (Oct 2026: SpiceDB resync
 * race returned brief 403s) must never turn a valid stop update into "refused".
 */
const RETRY_STATUSES = new Set([401, 403, 408, 425, 429]);

export function isRetryableReplayStatus(status: number): boolean {
  return status >= 500 || RETRY_STATUSES.has(status);
}

const TRANSIENT_REASONS =
  /(forbidden|unauthori[sz]ed|token|session|not_provisioned|driver_not_found|admin_forbidden|authz|too many|timeout)/i;

/** Parked by an older build for an auth/permission reason → safe to replay again. */
export function isTransientRejection(reason: string | undefined): boolean {
  return !!reason && TRANSIENT_REASONS.test(reason);
}

/** After this many auth/permission retries of the same action, treat it as a real refusal. */
export const MAX_AUTH_RETRIES = 12;

export function shouldPark(status: number, authAttempts: number): boolean {
  if (status < 400) return false;
  if (status >= 500) return false;
  if (!isRetryableReplayStatus(status)) return true;
  return (status === 401 || status === 403) && authAttempts >= MAX_AUTH_RETRIES;
}
