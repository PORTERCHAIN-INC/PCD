/**
 * Session-context helpers — SpiceDB permissions drive portal/module access.
 * Clerk is identity only; PostgreSQL holds business data, not ACLs.
 */

export type PorterchainPortal = "admin" | "merchant" | "driver" | "customer";

export type SessionContext = {
  user_id: string;
  status: string;
  onboarding_status: string;
  default_workspace: string | null;
  email: string | null;
  roles: string[];
  permissions: string[];
  modules?: string[];
  organization_ids?: string[];
  role_assignments?: Array<{
    role_key: string;
    scope_type: string;
    scope_id: string | null;
  }>;
  workspaces: Array<{
    id: string;
    label: string;
    kind: string;
    organization_id?: string | null;
  }>;
  legacy_profile_ids: Record<string, string>;
  auth?: {
    provider?: string;
    subject?: string | null;
    issuer?: string | null;
  };
};

/** Permission keys that gate each portal shell (must match UnifiedPermission). */
export const PORTAL_ACCESS_PERMISSION: Record<PorterchainPortal, string> = {
  admin: "platform.admin.access",
  merchant: "merchant_portal.access",
  driver: "driver_portal.access",
  customer: "customer_portal.access",
};

/** Login redirect priority after Platform Clerk sign-in. */
export const PORTAL_LOGIN_PRIORITY: readonly PorterchainPortal[] = [
  "admin",
  "merchant",
  "driver",
  "customer",
] as const;

export function hasPermission(
  permissions: string[] | ReadonlySet<string> | undefined,
  permission: string
): boolean {
  if (!permissions) return false;
  const set = permissions instanceof Set ? permissions : new Set(permissions);
  return set.has("system:all") || set.has(permission);
}

/**
 * Portal shell access. ``system:all`` implies Admin only — not merchant / driver /
 * customer (those require the explicit portal permission from a persona row).
 */
export function canAccessPortal(
  permissions: string[] | ReadonlySet<string> | undefined,
  portal: PorterchainPortal
): boolean {
  if (!permissions) return false;
  const set = permissions instanceof Set ? permissions : new Set(permissions);
  if (portal === "admin") {
    return set.has("system:all") || set.has(PORTAL_ACCESS_PERMISSION.admin);
  }
  return set.has(PORTAL_ACCESS_PERMISSION[portal]);
}

/**
 * Resolve which portal a signed-in user should enter.
 * Permission-only — never Clerk metadata, never stale role-name heuristics.
 */
export function resolvePortalFromSession(
  ctx: Pick<SessionContext, "permissions"> | null | undefined
): PorterchainPortal | null {
  const portals = portalsFromPermissions(ctx?.permissions);
  return portals[0] ?? null;
}

/** All portals the session may enter (for multi-persona workspace picker). */
export function portalsFromPermissions(
  permissions: string[] | ReadonlySet<string> | undefined
): PorterchainPortal[] {
  if (!permissions) return [];
  return PORTAL_LOGIN_PRIORITY.filter((portal) => canAccessPortal(permissions, portal));
}

export function workspacesForPortal(
  ctx: SessionContext | null | undefined,
  portal: PorterchainPortal
): SessionContext["workspaces"] {
  if (!ctx?.workspaces?.length) return [];
  const kindMap: Record<PorterchainPortal, string[]> = {
    admin: ["platform"],
    merchant: ["organization"],
    driver: ["driver"],
    customer: ["customer"],
  };
  const kinds = new Set(kindMap[portal]);
  return ctx.workspaces.filter((w) => kinds.has(w.kind));
}

const SESSION_CONTEXT_TIMEOUT_MS = 12_000;

export async function fetchSessionContext(
  apiBaseUrl: string,
  token: string
): Promise<SessionContext> {
  const base = apiBaseUrl.replace(/\/$/, "");
  let res: Response;
  try {
    res = await fetch(`${base}/v1/auth/session-context`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(SESSION_CONTEXT_TIMEOUT_MS),
    });
  } catch (err) {
    if (err instanceof Error && (err.name === "TimeoutError" || err.name === "AbortError")) {
      throw new Error("Failed to fetch");
    }
    throw err;
  }
  if (!res.ok) {
    let detail = `session_context_${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* ignore non-JSON bodies */
    }
    throw new Error(detail);
  }
  return (await res.json()) as SessionContext;
}
