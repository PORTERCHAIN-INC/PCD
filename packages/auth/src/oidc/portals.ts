/**
 * One shared Keycloak sign-in page for every portal; after sign-in the user's realm roles decide
 * which portal they land in, whichever portal they started from (Ravi 2026-11-04).
 */
export type Portal = "admin" | "merchant" | "driver" | "customer";

/** Highest-privilege first: a user with several personas lands on the first one they hold. */
export const PORTAL_ORDER: Portal[] = ["admin", "merchant", "driver", "customer"];

const STAFF_ROLES = new Set([
  "super_admin",
  "admin",
  "dispatcher",
  "support",
  "support_lead",
  "sales",
  "sales_manager",
  "finance",
  "compliance",
  "developer",
  "marketing",
  "read_only",
  "fleet_manager",
]);

const CLIENT_PORTAL: Record<string, Portal> = {
  "pc-admin": "admin",
  "pc-merchant-portal": "merchant",
  "pc-driver-portal": "driver",
  "pc-customer-portal": "customer",
};

export function portalForClient(clientId: string): Portal | null {
  return CLIENT_PORTAL[clientId] ?? null;
}

export function portalsForRoles(roles: readonly string[]): Portal[] {
  const has = (p: Portal) =>
    roles.some((r) =>
      p === "admin" ? STAFF_ROLES.has(r) : p === "merchant" ? r.startsWith("merchant_") : r === p
    );
  const held = PORTAL_ORDER.filter(has);
  // "customer" is the realm default role, so everyone holds it: it only counts when no other persona does.
  const personas = held.filter((p) => p !== "customer");
  return personas.length > 0 ? personas : held;
}

/** Portal this user should be in, or null to stay (allowed here, no persona role, or not a portal app). */
export function portalRedirect(current: Portal | null, roles: readonly string[]): Portal | null {
  if (!current) return null;
  const allowed = portalsForRoles(roles);
  if (allowed.length === 0 || allowed.includes(current)) return null;
  return allowed[0] ?? null;
}

/**
 * Base URL of another portal: PC_PORTAL_URL_<NAME> (e.g. local stack ports), else swap the first
 * host label (admin.porterchain.com -> driver.porterchain.com). Null when it cannot be derived.
 */
export function portalOrigin(
  target: Portal,
  current: Portal,
  origin: string,
  env: Record<string, string | undefined> = process.env
): string | null {
  const fromEnv = (env[`PC_PORTAL_URL_${target.toUpperCase()}`] ?? "").trim().replace(/\/+$/, "");
  if (fromEnv) return fromEnv;
  try {
    const u = new URL(origin);
    const [first, ...rest] = u.hostname.split(".");
    if (first !== current || rest.length < 2) return null;
    u.hostname = [target, ...rest].join(".");
    return u.origin;
  } catch {
    return null;
  }
}

/**
 * Website (pc-website) sign-in: after Keycloak, send the user to the portal their roles allow.
 */
export function websitePortalRedirect(clientId: string, roles: readonly string[]): Portal | null {
  if (clientId !== "pc-website") return null;
  return portalsForRoles(roles)[0] ?? null;
}

/** Portal base URL from the website: PC_PORTAL_URL_<NAME>, else <portal>.<site domain>. */
export function websitePortalOrigin(
  target: Portal,
  origin: string,
  env: Record<string, string | undefined> = process.env
): string | null {
  const fromEnv = (env[`PC_PORTAL_URL_${target.toUpperCase()}`] ?? "").trim().replace(/\/+$/, "");
  if (fromEnv) return fromEnv;
  try {
    const u = new URL(origin);
    const host = u.hostname.replace(/^www\./, "");
    if (u.port || host.split(".").length < 2) return null;
    u.hostname = `${target}.${host}`;
    return u.origin;
  } catch {
    return null;
  }
}
