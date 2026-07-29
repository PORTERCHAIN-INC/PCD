import { getPorterchainApiBase } from "@/lib/api-base";
import {
  adminPortalDashboardUrl,
  customerPortalDashboardUrl,
  driverSignInUrl,
  merchantPortalUrl,
} from "@/data/portal-links";
import {
  fetchSessionContext as fetchSharedSessionContext,
  portalsFromPermissions,
  resolvePortalFromSession,
  type PorterchainPortal,
  type SessionContext,
} from "@porterchain/auth";

export type AuthMe = {
  user_id: string;
  user_type: string;
  email?: string | null;
  role?: string | null;
  status?: string | null;
  roles?: string[];
  /** Prefer this over `user_type` for portal routing — same permission keys as session-context. */
  permissions?: string[];
};

export type { SessionContext };

const PORTAL_HOME: Record<PorterchainPortal, string> = {
  admin: adminPortalDashboardUrl,
  merchant: merchantPortalUrl,
  driver: driverSignInUrl,
  customer: customerPortalDashboardUrl,
};

const PORTAL_LABEL: Record<PorterchainPortal, string> = {
  admin: "Admin",
  merchant: "Merchant",
  driver: "Driver",
  customer: "Customer",
};

/** Avoid infinite "Opening your portal…" when the API accept-queue is dead. */
const AUTH_FETCH_TIMEOUT_MS = 12_000;

export async function fetchAuthMe(token: string): Promise<AuthMe> {
  let res: Response;
  try {
    res = await fetch(`${getPorterchainApiBase()}/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(AUTH_FETCH_TIMEOUT_MS),
    });
  } catch (err) {
    if (err instanceof Error && (err.name === "TimeoutError" || err.name === "AbortError")) {
      throw new Error("Failed to fetch");
    }
    throw err;
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "auth_failed");
  }
  return res.json();
}

export async function fetchSessionContext(token: string): Promise<SessionContext> {
  return fetchSharedSessionContext(getPorterchainApiBase(), token);
}

/**
 * After Platform Clerk sign-in, send the user to the module they are provisioned for.
 * Permission-only (admin → merchant → driver → customer).
 */
export function portalHomeUrlFromSession(ctx: SessionContext): string | null {
  const portal = resolvePortalFromSession(ctx);
  return portal ? PORTAL_HOME[portal] : null;
}

/** Multi-persona: every portal this session may open (for workspace picker). */
export function portalChoicesFromSession(
  ctx: Pick<SessionContext, "permissions">
): Array<{ portal: PorterchainPortal; url: string; label: string }> {
  return portalsFromPermissions(ctx.permissions).map((portal) => ({
    portal,
    url: PORTAL_HOME[portal],
    label: PORTAL_LABEL[portal],
  }));
}

/**
 * Fallback when session-context is unavailable but `/v1/auth/me` still returned
 * `permissions` — map them the same permission-only way as session-context.
 */
export function portalHomeUrlFromPermissions(permissions: string[]): string | null {
  const portal = resolvePortalFromSession({ permissions });
  return portal ? PORTAL_HOME[portal] : null;
}

/**
 * Last-resort fallback when neither session-context nor `/v1/auth/me.permissions`
 * are available — exclusive `user_type` hint. Deprecated; do not use when
 * permissions are present on either response.
 */
export function portalHomeUrlFromAuthMe(me: AuthMe): string | null {
  const t = (me.user_type || "").toLowerCase();
  if (t === "admin" || t === "dispatcher" || t === "support" || t === "sales") {
    return PORTAL_HOME.admin;
  }
  if (t === "merchant") return PORTAL_HOME.merchant;
  if (t === "driver") return PORTAL_HOME.driver;
  if (t === "customer") return PORTAL_HOME.customer;
  // Never invent a portal for unprovisioned / unknown — forces explicit error UI.
  return null;
}

export function customerPortalHomeUrl(): string {
  return customerPortalDashboardUrl;
}

export function isCustomerUserType(userType: string): boolean {
  return userType.toLowerCase() === "customer";
}
