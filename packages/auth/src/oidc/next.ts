/**
 * Next.js glue for Keycloak OIDC (L36): /auth/* route handlers, the edge middleware gate and
 * a server-side `auth()` for route handlers / server components.
 */
import { NextResponse, type NextRequest } from "next/server";
import {
  FLOW_COOKIE,
  SESSION_COOKIE,
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

/** Refresh token lifetime cap for the cookie (Keycloak SSO max is shorter and wins). */
const SESSION_MAX_AGE = 60 * 60 * 12;
const secure = () => process.env.NODE_ENV === "production";

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
  const raw = readChunks(cookies, SESSION_COOKIE);
  return raw ? unseal<Session>(raw, c.secret) : null;
}

export async function sessionCookies(s: Session, c: OidcConfig): Promise<CookieSpec[]> {
  return chunkCookies(SESSION_COOKIE, await seal(s, c.secret), SESSION_MAX_AGE);
}

function notConfigured() {
  return NextResponse.json({ detail: "auth_not_configured" }, { status: 503 });
}

/** GET /auth/login?return_to=/x&register=1&idp=google */
async function login(req: NextRequest, c: OidcConfig) {
  const q = req.nextUrl.searchParams;
  const flow = newFlow(safeReturnTo(q.get("return_to") ?? q.get("redirect_url")));
  const redirectUri = `${appOrigin(c, req.url, req.headers)}/auth/callback`;
  const url = await authorizeUrl(c, redirectUri, flow, {
    register: q.get("register") === "1",
    idpHint: q.get("idp") ?? undefined,
    loginHint: q.get("login_hint") ?? undefined,
  });
  const res = NextResponse.redirect(url);
  res.cookies.set(FLOW_COOKIE, await seal(flow, c.secret), {
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
  const raw = req.cookies.get(FLOW_COOKIE)?.value;
  const flow = raw ? await unseal<Flow>(raw, c.secret) : null;
  const fail = (code: string) => {
    const res = NextResponse.redirect(
      `${origin}${c.signInPath}?auth_error=${encodeURIComponent(code)}`
    );
    res.cookies.set(FLOW_COOKIE, "", { path: "/auth", maxAge: 0 });
    return res;
  };
  if (q.get("error")) return fail(q.get("error") ?? "access_denied");
  if (!flow || !q.get("state") || q.get("state") !== flow.state) return fail("state_mismatch");
  const code = q.get("code");
  if (!code) return fail("missing_code");
  try {
    const s = await exchangeCode(c, code, flow.verifier, `${origin}/auth/callback`);
    const res = NextResponse.redirect(`${origin}${flow.returnTo}`);
    res.cookies.set(FLOW_COOKIE, "", { path: "/auth", maxAge: 0 });
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
  return apply(res, clearCookies(SESSION_COOKIE));
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
        clearCookies(SESSION_COOKIE)
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
  if (isPublic(path, o.publicPaths) || o.allow?.(req)) return NextResponse.next();
  const c = oidcConfig();
  const signIn = o.signInPath ?? "/sign-in";
  const deny = () => {
    if (path.startsWith("/api/")) {
      return NextResponse.json({ detail: "missing_bearer_token" }, { status: 401 });
    }
    const u = new URL(signIn, req.url);
    const back = `${path}${req.nextUrl.search}`;
    if (back !== signIn) u.searchParams.set("redirect_url", back);
    return NextResponse.redirect(u);
  };
  if (!c) return deny();
  let s = await readSession(req.cookies, c);
  if (!s) return deny();
  if (!needsRefresh(s)) return NextResponse.next();
  try {
    s = await refreshSession(c, s);
  } catch {
    return apply(deny(), clearCookies(SESSION_COOKIE));
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
