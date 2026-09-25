/**
 * Edge session *hint* for Clerk portals — same posture as admin ``pc_staff_sid``.
 *
 * Admin middleware only checks cookie *presence*; real auth is BFF/API.
 * Clerk portals historically called ``await auth()`` on every matched request
 * (pages + ``/api``), which decrypts/handshakes the session on soft-nav and
 * BFF hops. When Clerk has already set a signed-in client cookie, skip that
 * and let AccessGate + API Bearer enforce identity (same split as admin).
 *
 * Cookie names follow Clerk's defaults (``__client_uat`` / ``__session``) and
 * common prefixed variants for multi-domain setups.
 */

export type CookieReader = {
  get: (name: string) => { value: string } | undefined;
  getAll?: () => Array<{ name: string; value: string }>;
};

function isSignedInUat(value: string | undefined): boolean {
  return Boolean(value && value !== "0");
}

function isSessionJwt(value: string | undefined): boolean {
  return Boolean(value && value.length > 0);
}

/** True when cookies indicate a signed-in Clerk client (not a cryptographic verify). */
export function hasClerkSessionHint(cookies: CookieReader): boolean {
  if (isSignedInUat(cookies.get("__client_uat")?.value)) return true;
  if (isSessionJwt(cookies.get("__session")?.value)) return true;

  const all = typeof cookies.getAll === "function" ? cookies.getAll() : [];
  for (const { name, value } of all) {
    if (name === "__client_uat" || name.endsWith("__client_uat")) {
      if (isSignedInUat(value)) return true;
      continue;
    }
    if (name === "__session" || name.endsWith("__session")) {
      if (isSessionJwt(value)) return true;
    }
  }
  return false;
}
