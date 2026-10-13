/** Staff IdP session helpers — HttpOnly cookie via BFF (no JS bearer SoT). */

/** Sentinel for adminFetch / session gate: BFF attaches Bearer from cookie. */
export const STAFF_COOKIE_TOKEN = "staff_cookie";

/** Dispatched after establishStaffCookie so AdminAuthProvider re-probes. */
export const STAFF_AUTH_EVENT = "pc-staff-auth";

/** Establish admin-origin HttpOnly cookie from a one-time API bearer (login/activate). */
export async function establishStaffCookie(bearerToken: string): Promise<void> {
  const res = await fetch("/api/auth/staff-session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bearer_token: bearerToken }),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(typeof body.detail === "string" ? body.detail : "staff_cookie_failed");
  }
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(STAFF_AUTH_EVENT));
  }
}

export async function probeStaffCookie(): Promise<boolean> {
  try {
    const res = await fetch("/api/auth/staff-session", { cache: "no-store" });
    if (!res.ok) return false;
    const body = (await res.json()) as { authenticated?: boolean };
    return Boolean(body.authenticated);
  } catch {
    return false;
  }
}

export const LOGOUT_TIMEOUT_MS = 3000;

/** fetch that never throws and never waits longer than `ms`. */
async function quietFetch(url: string, init: RequestInit, ms: number): Promise<void> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), ms);
  try {
    await fetch(url, { ...init, signal: ctl.signal });
  } catch {
    /* offline / API down — sign-out must still succeed */
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Sign out that works even when the API is down.
 * Revoke (best-effort, bounded) and drop the local cookie in parallel —
 * the BFF reads the cookie when the request starts, so revoke still carries the bearer.
 */
export async function clearStaffSession(apiUrl?: string): Promise<void> {
  const post: RequestInit = { method: "POST", credentials: "include" };
  const revoke = [quietFetch("/api/porterchain/v1/auth/staff/logout", post, LOGOUT_TIMEOUT_MS)];
  if (apiUrl) {
    revoke.push(
      quietFetch(`${apiUrl.replace(/\/$/, "")}/v1/auth/staff/logout`, post, LOGOUT_TIMEOUT_MS)
    );
  }
  await Promise.all([
    ...revoke,
    quietFetch("/api/auth/staff-session", { method: "DELETE" }, LOGOUT_TIMEOUT_MS),
  ]);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(STAFF_AUTH_EVENT));
  }
}
