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

/** Clear browser cookie + revoke API session (best-effort). */
export async function clearStaffSession(apiUrl?: string): Promise<void> {
  // Revoke while cookie still present so BFF can attach Bearer.
  try {
    await fetch("/api/porterchain/v1/auth/staff/logout", {
      method: "POST",
      credentials: "include",
    });
  } catch {
    /* ignore */
  }
  if (apiUrl) {
    try {
      await fetch(`${apiUrl.replace(/\/$/, "")}/v1/auth/staff/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      /* ignore */
    }
  }
  try {
    await fetch("/api/auth/staff-session", { method: "DELETE" });
  } catch {
    /* ignore */
  }
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(STAFF_AUTH_EVENT));
  }
}
