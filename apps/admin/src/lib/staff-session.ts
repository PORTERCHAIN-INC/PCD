/** Local staff IdP bearer (cross-port cookie not reliable on localhost). */

const STORAGE_KEY = "pc_staff_sess_bearer";

export function getStaffBearer(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStaffBearer(bearerToken: string): void {
  sessionStorage.setItem(STORAGE_KEY, bearerToken);
}

export function clearStaffBearer(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/** Clear browser + API staff session (safe to call when none exists). */
export async function clearStaffSession(apiUrl?: string): Promise<void> {
  const bearer = getStaffBearer();
  clearStaffBearer();
  try {
    await fetch("/api/auth/staff-session", { method: "DELETE" });
  } catch {
    /* ignore */
  }
  if (bearer && apiUrl) {
    try {
      await fetch(`${apiUrl}/v1/auth/staff/logout`, {
        method: "POST",
        credentials: "include",
        headers: { Authorization: `Bearer ${bearer}` },
      });
    } catch {
      /* ignore */
    }
  }
}
