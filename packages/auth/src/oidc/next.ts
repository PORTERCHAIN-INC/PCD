/**
 * Next.js glue for Keycloak OIDC (L36): /auth/* route handlers, the edge middleware gate and
 * a server-side `auth()` for route handlers / server components.
 */
import { NextResponse, type NextRequest } from "next/server";
import { cookieSecure } from "../cookieSecure";
import {
  flowCookieName,
  hasSessionCookie,
  sessionCookieName,
  appOrigin,
  authorizeUrl,
  chunkCookies,
  clearCookies,
  endpoints,
  exchangeCode,
  logoutUrl,
  needsRefresh,
  newFlow,
  oidcConfig,
  readChunks,
  refreshSession,
  revokeSession,
  safeReturnTo,
  seal,
  unseal,
  type CookieReader,
  type CookieSpec,
  type Flow,
  type OidcConfig,
  type Session,
  type SessionUser,
} from "./core";
import { portalForClient, portalOrigin, portalRedirect } from "./portals";

/** Refresh token lifetime cap for the cookie (Keycloak SSO max is shorter and wins). */
const SESSION_MAX_AGE = 60 * 60 * 12;
// AUTH_COOKIE_SECURE=false only for a plain-http LAN test stack (scripts/local-stack.sh); prod keeps Secure.
const secure = () => cookieSecure();

function apply(res: NextResponse, specs: CookieSpec[]) {
  for (const s of specs) {
    res.cookies.set(s.name, s.value, {
      httpOnly: true,
      secure: secure(),
      sameSite: "lax",
      path: "/",
      maxAge: s.maxAge,
    });
  }
  return res;
}

export async function readSession(cookies: CookieReader, c: OidcConfig): Promise<Session | null> {
  const raw = readChunks(cookies, sessionCookieName());
  return raw ? unseal<Session>(raw, c.secret) : null;
}

export async function sessionCookies(s: Session, c: OidcConfig): Promise<CookieSpec[]> {
  return chunkCookies(sessionCookieName(), await seal(s, c.secret), SESSION_MAX_AGE);
}

function notConfigured() {
  return NextResponse.json({ detail: "auth_not_configured" }, { status: 503 });
}

/** GET /auth/login?return_to=/x&register=1&idp=google&prompt=login (prompt=login forces re-auth for step-up) */
async function login(req: NextRequest, c: OidcConfig) {
  const q = req.nextUrl.searchParams;
  const flow = newFlow(safeReturnTo(q.get("return_to") ?? q.get("redirect_url")));
  // Website sign-in hands off with ?sso=1 on the target page: reuse that fresh Keycloak session.
  const ssoHandoff = /[?&]sso=1(&|$)/.test(flow.returnTo);
  const redirectUri = `${appOrigin(c, req.url, req.headers)}/auth/callback`;
  const url = await authorizeUrl(c, redirectUri, flow, {
    register: q.get("register") === "1",
    idpHint: q.get("idp") ?? undefined,
    loginHint: q.get("login_hint") ?? undefined,
    // OIDC_PROMPT_LOGIN=1: persona apps always show the Keycloak form, so an SSO session from another
    // persona (e.g. admin) in the same browser is never silently reused.
    prompt:
      q.get("prompt") === "login" || (process.env.OIDC_PROMPT_LOGIN === "1" && !ssoHandoff)
        ? "login"
        : undefined,
  });
  // Keycloak pages follow the app language (pc_locale cookie set by the EN/FR switcher).
  const ui = req.cookies.get("pc_locale")?.value;
  const target = new URL(url);
  if (ui === "fr" || ui === "en") target.searchParams.set("ui_locales", ui);
  const res = NextResponse.redirect(target.toString());
  res.cookies.set(flowCookieName(), await seal(flow, c.secret), {
    httpOnly: true,
    secure: secure(),
    sameSite: "lax",
    path: "/auth",
    maxAge: 600,
  });
  return res;
}

async function callback(req: NextRequest, c: OidcConfig) {
  const origin = appOrigin(c, req.url, req.headers);
  const q = req.nextUrl.searchParams;
  const raw = req.cookies.get(flowCookieName())?.value;
  const flow = raw ? await unseal<Flow>(raw, c.secret) : null;
  const fail = (code: string) => {
    const res = NextResponse.redirect(
      `${origin}${c.signInPath}?auth_error=${encodeURIComponent(code)}`
    );
    res.cookies.set(flowCookieName(), "", { path: "/auth", maxAge: 0 });
    return res;
  };
  if (q.get("error")) return fail(q.get("error") ?? "access_denied");
  if (!flow || !q.get("state") || q.get("state") !== flow.state) return fail("state_mismatch");
  const code = q.get("code");
  if (!code) return fail("missing_code");
  try {
    const s = await exchangeCode(c, code, flow.verifier, `${origin}/auth/callback`);
    // Shared sign-in page: land the user in the portal their roles allow (Keycloak SSO signs them in there).
    const here = portalForClient(c.clientId);
    const target = portalRedirect(here, s.user.roles);
    const dest = target && here ? portalOrigin(target, here, origin) : null;
    if (dest) {
      const res = NextResponse.redirect(
        `${dest}/auth/login?return_to=${encodeURIComponent("/?sso=1")}`
      );
      res.cookies.set(flowCookieName(), "", { path: "/auth", maxAge: 0 });
      return res;
    }
    const res = NextResponse.redirect(`${origin}${flow.returnTo}`);
    res.cookies.set(flowCookieName(), "", { path: "/auth", maxAge: 0 });
    res.cookies.set(HOP_COOKIE, "", { path: "/", maxAge: 0 });
    return apply(res, await sessionCookies(s, c));
  } catch (e) {
    return fail(e instanceof Error ? e.message : "token_exchange_failed");
  }
}

async function logout(req: NextRequest, c: OidcConfig) {
  const origin = appOrigin(c, req.url, req.headers);
  const s = await readSession(req.cookies, c);
  const back = `${origin}${safeReturnTo(req.nextUrl.searchParams.get("return_to") ?? c.signInPath)}`;
  if (s) await revokeSession(c, s);
  const res = NextResponse.redirect(s ? logoutUrl(c, back, s.idToken) : back);
  return apply(res, clearCookies(sessionCookieName()));
}

/** GET /auth/session → { signedIn, user, accessToken, expiresAt }; refreshes when due. */
async function session(req: NextRequest, c: OidcConfig) {
  let s = await readSession(req.cookies, c);
  const headers = { "Cache-Control": "no-store" };
  if (!s) return NextResponse.json({ signedIn: false }, { headers });
  let specs: CookieSpec[] = [];
  if (needsRefresh(s) || req.nextUrl.searchParams.get("fresh") === "1") {
    try {
      s = await refreshSession(c, s);
      specs = await sessionCookies(s, c);
    } catch {
      return apply(
        NextResponse.json({ signedIn: false }, { headers }),
        clearCookies(sessionCookieName())
      );
    }
  }
  return apply(
    NextResponse.json(
      { signedIn: true, user: s.user, accessToken: s.accessToken, expiresAt: s.expiresAt },
      { headers }
    ),
    specs
  );
}

/** Route handler for app/auth/[action]/route.ts */
export async function handleAuthRoute(
  req: NextRequest,
  ctx: { params: Promise<{ action: string }> }
): Promise<Response> {
  const c = oidcConfig();
  if (!c) return notConfigured();
  const { action } = await ctx.params;
  switch (action) {
    case "login":
      return login(req, c);
    case "register": {
      req.nextUrl.searchParams.set("register", "1");
      return login(req, c);
    }
    case "callback":
      return callback(req, c);
    case "logout":
      return logout(req, c);
    case "session":
      return session(req, c);
    case "account":
      return NextResponse.redirect(endpoints(c).account);
    default:
      return NextResponse.json({ detail: "not_found" }, { status: 404 });
  }
}

const HOP_COOKIE = "pc_auth_hop";

/** Send a signed-out browser straight to Keycloak; a second bounce within 15 s shows the error page instead of looping. */
function toKeycloak(req: NextRequest, signIn: string, back: string | null): NextResponse {
  if (req.cookies.get(HOP_COOKIE)?.value) {
    const res = NextResponse.redirect(new URL(`${signIn}?auth_error=sign_in_loop`, req.url));
    res.cookies.set(HOP_COOKIE, "", { path: "/", maxAge: 0 });
    return res;
  }
  const u = new URL("/auth/login", req.url);
  if (back && back !== signIn) u.searchParams.set("return_to", back);
  const res = NextResponse.redirect(u);
  res.cookies.set(HOP_COOKIE, "1", {
    path: "/",
    maxAge: 15,
    httpOnly: true,
    sameSite: "lax",
    secure: secure(),
  });
  return res;
}

export type AuthGateOptions = {
  /** Path prefixes that never need a session (/auth is always public). */
  publicPaths: string[];
  /** Where to send signed-out browsers; default /sign-in. */
  signInPath?: string;
  /** Extra pass-through check (e.g. impersonation cookie). */
  allow?: (req: NextRequest) => boolean;
};

function isPublic(path: string, prefixes: string[]) {
  return (
    path.startsWith("/auth/") ||
    prefixes.some(
      (p) =>
        path === p ||
        path.startsWith(`${p}/`) ||
        (p.endsWith("(.*)") && path.startsWith(p.slice(0, -4)))
    )
  );
}

/**
 * Edge gate: refreshes a due access token (and forwards it to this request) or redirects to
 * sign-in. API routes get 401 JSON instead of a redirect.
 */
export async function authGate(req: NextRequest, o: AuthGateOptions): Promise<NextResponse> {
  const path = req.nextUrl.pathname;
  const signIn = o.signInPath ?? "/sign-in";
  // The portal sign-in page only reports errors now; signed-out visits go straight to Keycloak.
  if (
    path === signIn &&
    !req.nextUrl.searchParams.get("auth_error") &&
    !hasSessionCookie(req.cookies)
  ) {
    return toKeycloak(req, signIn, req.nextUrl.searchParams.get("redirect_url"));
  }
  if (isPublic(path, o.publicPaths) || o.allow?.(req)) return NextResponse.next();
  const c = oidcConfig();
  const deny = () => {
    if (path.startsWith("/api/")) {
      return NextResponse.json({ detail: "missing_bearer_token" }, { status: 401 });
    }
    // Straight to the shared Keycloak page (no portal pre-login screen); errors come back to signIn.
    return toKeycloak(req, signIn, `${path}${req.nextUrl.search}`);
  };
  if (!c) return deny();
  let s = await readSession(req.cookies, c);
  if (!s) return deny();
  if (!needsRefresh(s)) return NextResponse.next();
  try {
    s = await refreshSession(c, s);
  } catch {
    return apply(deny(), clearCookies(sessionCookieName()));
  }
  const specs = await sessionCookies(s, c);
  // Forward the refreshed cookies to this request so server code sees the new token.
  const fwd = new Headers(req.headers);
  const jar = new Map(req.cookies.getAll().map((x) => [x.name, x.value]));
  for (const sp of specs) {
    if (sp.maxAge) jar.set(sp.name, sp.value);
    else jar.delete(sp.name);
  }
  fwd.set("cookie", [...jar].map(([k, v]) => `${k}=${v}`).join("; "));
  return apply(NextResponse.next({ request: { headers: fwd } }), specs);
}

export type ServerAuth = {
  userId: string | null;
  user: SessionUser | null;
  /** Current access token (middleware keeps it fresh). */
  getToken: () => Promise<string | null>;
};

/** Server-side session (route handlers / server components). */
export async function auth(): Promise<ServerAuth> {
  const c = oidcConfig();
  const { cookies } = await import("next/headers");
  const jar = await cookies();
  const s = c ? await readSession(jar, c) : null;
  if (!c || !s) return { userId: null, user: null, getToken: async () => null };
  return { userId: s.user.id || null, user: s.user, getToken: async () => s.accessToken };
}

export type PortalMiddlewareOptions = AuthGateOptions & {
  /** Local-only shortcuts (dev bearer, forgeable dev cookies). Must return false in prod builds. */
  devPassThrough?: (req: NextRequest) => boolean;
};

const hasImpersonation = (req: NextRequest) =>
  Boolean(req.cookies.get("pc_imp_bearer")?.value?.startsWith("pc_imp_"));

/** Standard portal middleware: dev bypass → impersonation → Keycloak session gate. */
export function portalMiddleware(o: PortalMiddlewareOptions) {
  return async function middleware(req: NextRequest): Promise<NextResponse> {
    if (o.devPassThrough?.(req)) return NextResponse.next();
    return authGate(req, {
      ...o,
      allow: (r) => hasImpersonation(r) || Boolean(o.allow?.(r)),
    });
  };
}

export const PORTAL_MATCHER = [
  "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest|txt)).*)",
  "/(api|trpc)(.*)",
];
