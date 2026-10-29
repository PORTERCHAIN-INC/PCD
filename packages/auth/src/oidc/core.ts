/**
 * Keycloak OIDC for the web portals (L36): authorization code + PKCE (S256), tokens kept
 * server-side in an AES-GCM encrypted, httpOnly, chunked cookie. Pure WebCrypto, so the
 * same code runs in middleware (Edge) and route handlers (Node). No React / Next imports.
 */

export const SESSION_COOKIE = "pc_session";
export const FLOW_COOKIE = "pc_oidc_flow";
const CHUNK = 3800;
const MAX_CHUNKS = 6;
/** Refresh when the access token has less than this left. */
export const REFRESH_SKEW_S = 60;

export type OidcConfig = {
  /** Public issuer base, e.g. https://auth.porterchain.com */
  url: string;
  /** Server-to-Keycloak base (container network); defaults to url. */
  internalUrl: string;
  realm: string;
  clientId: string;
  secret: string;
  /** Absolute app origin for redirect_uri; derived from the request when empty. */
  appUrl: string;
  /** App page that shows sign-in errors (driver portal: /login). */
  signInPath: string;
};

export type SessionUser = {
  id: string;
  email: string | null;
  emailVerified: boolean;
  firstName: string | null;
  lastName: string | null;
  fullName: string | null;
  username: string | null;
  roles: string[];
};

export type Session = {
  accessToken: string;
  refreshToken: string;
  idToken?: string;
  /** Access token expiry, epoch seconds. */
  expiresAt: number;
  user: SessionUser;
};

export type CookieReader = { get(name: string): { value: string } | undefined };
export type CookieSpec = { name: string; value: string; maxAge: number };

type Env = Record<string, string | undefined>;

export function oidcConfig(env: Env = process.env): OidcConfig | null {
  const url = (env.KEYCLOAK_URL ?? env.NEXT_PUBLIC_KEYCLOAK_URL ?? "").trim().replace(/\/+$/, "");
  const clientId = (env.KEYCLOAK_CLIENT_ID ?? env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "").trim();
  const secret = (env.AUTH_SESSION_SECRET ?? "").trim();
  if (!url || !clientId || secret.length < 32) return null;
  return {
    url,
    internalUrl: (env.KEYCLOAK_INTERNAL_URL ?? "").trim().replace(/\/+$/, "") || url,
    realm: (env.KEYCLOAK_REALM ?? "porterchain").trim() || "porterchain",
    clientId,
    secret,
    appUrl: (env.APP_URL ?? env.NEXT_PUBLIC_APP_URL ?? "").trim().replace(/\/+$/, ""),
    signInPath: (env.AUTH_SIGN_IN_PATH ?? "").trim() || "/sign-in",
  };
}

export function issuer(c: OidcConfig): string {
  return `${c.url}/realms/${c.realm}`;
}

export function endpoints(c: OidcConfig) {
  const pub = `${issuer(c)}/protocol/openid-connect`;
  const internal = `${c.internalUrl}/realms/${c.realm}/protocol/openid-connect`;
  return {
    authorize: `${pub}/auth`,
    logout: `${pub}/logout`,
    token: `${internal}/token`,
    revoke: `${internal}/revoke`,
    account: `${issuer(c)}/account`,
  };
}

// ---------- encoding / crypto ----------

const te = new TextEncoder();
const td = new TextDecoder();

export function b64url(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function unb64url(s: string): Uint8Array {
  const p = s.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(p + "===".slice((p.length + 3) % 4));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export function randomToken(bytes = 32): string {
  return b64url(crypto.getRandomValues(new Uint8Array(bytes)));
}

export async function pkceChallenge(verifier: string): Promise<string> {
  const d = await crypto.subtle.digest("SHA-256", te.encode(verifier));
  return b64url(new Uint8Array(d));
}

const keyCache = new Map<string, Promise<CryptoKey>>();
function key(secret: string): Promise<CryptoKey> {
  let k = keyCache.get(secret);
  if (!k) {
    k = crypto.subtle
      .digest("SHA-256", te.encode(`pc-session-v1:${secret}`))
      .then((raw) => crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt", "decrypt"]));
    keyCache.set(secret, k);
  }
  return k;
}

export async function seal(value: unknown, secret: string): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    await key(secret),
    te.encode(JSON.stringify(value))
  );
  return `${b64url(iv)}.${b64url(new Uint8Array(ct))}`;
}

export async function unseal<T>(sealed: string, secret: string): Promise<T | null> {
  const [iv, ct] = sealed.split(".");
  if (!iv || !ct) return null;
  try {
    const pt = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: unb64url(iv) as BufferSource },
      await key(secret),
      unb64url(ct) as BufferSource
    );
    return JSON.parse(td.decode(pt)) as T;
  } catch {
    return null;
  }
}

// ---------- cookies ----------

/** Split a sealed value over pc_session.0..n; returns specs that also clear unused chunks. */
export function chunkCookies(name: string, value: string, maxAge: number): CookieSpec[] {
  const parts: string[] = [];
  for (let i = 0; i < value.length; i += CHUNK) parts.push(value.slice(i, i + CHUNK));
  if (parts.length > MAX_CHUNKS) throw new Error("session_too_large");
  const out: CookieSpec[] = parts.map((v, i) => ({ name: `${name}.${i}`, value: v, maxAge }));
  for (let i = parts.length; i < MAX_CHUNKS; i++)
    out.push({ name: `${name}.${i}`, value: "", maxAge: 0 });
  return out;
}

export function clearCookies(name: string): CookieSpec[] {
  return Array.from({ length: MAX_CHUNKS }, (_, i) => ({
    name: `${name}.${i}`,
    value: "",
    maxAge: 0,
  }));
}

export function readChunks(cookies: CookieReader, name: string): string {
  let s = "";
  for (let i = 0; i < MAX_CHUNKS; i++) {
    const v = cookies.get(`${name}.${i}`)?.value;
    if (!v) break;
    s += v;
  }
  return s;
}

export function hasSessionCookie(cookies: CookieReader): boolean {
  return Boolean(cookies.get(`${SESSION_COOKIE}.0`)?.value);
}

// ---------- tokens ----------

export function decodeJwt(token: string): Record<string, unknown> {
  const part = token.split(".")[1];
  if (!part) return {};
  try {
    return JSON.parse(td.decode(unb64url(part))) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function str(v: unknown): string | null {
  return typeof v === "string" && v ? v : null;
}

export function userFromTokens(accessToken: string, idToken?: string): SessionUser {
  const a = decodeJwt(accessToken);
  const i = idToken ? decodeJwt(idToken) : {};
  const pick = (k: string) => str(i[k]) ?? str(a[k]);
  const roles = Array.isArray(a.pc_roles)
    ? (a.pc_roles as unknown[]).filter((r): r is string => typeof r === "string")
    : [];
  return {
    id: pick("sub") ?? "",
    email: pick("email"),
    emailVerified: Boolean(i.email_verified ?? a.email_verified),
    firstName: pick("given_name"),
    lastName: pick("family_name"),
    fullName: pick("name"),
    username: pick("preferred_username"),
    roles,
  };
}

type TokenResponse = {
  access_token: string;
  refresh_token?: string;
  id_token?: string;
  expires_in?: number;
  refresh_expires_in?: number;
};

export function sessionFromTokens(t: TokenResponse, prev?: Session, now = Date.now()): Session {
  const exp = Number(decodeJwt(t.access_token).exp);
  const idToken = t.id_token ?? prev?.idToken;
  return {
    accessToken: t.access_token,
    refreshToken: t.refresh_token ?? prev?.refreshToken ?? "",
    idToken,
    expiresAt: Number.isFinite(exp) ? exp : Math.floor(now / 1000) + (t.expires_in ?? 300),
    user: userFromTokens(t.access_token, idToken),
  };
}

export function needsRefresh(s: Session, now = Date.now()): boolean {
  return s.expiresAt - REFRESH_SKEW_S <= Math.floor(now / 1000);
}

async function tokenCall(c: OidcConfig, form: Record<string, string>, fetcher: typeof fetch) {
  const res = await fetcher(endpoints(c).token, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_id: c.clientId, ...form }).toString(),
    cache: "no-store",
  });
  const body = (await res.json().catch(() => ({}))) as TokenResponse & { error?: string };
  if (!res.ok || !body.access_token) throw new Error(body.error || `token_http_${res.status}`);
  return body;
}

export async function exchangeCode(
  c: OidcConfig,
  code: string,
  verifier: string,
  redirectUri: string,
  fetcher: typeof fetch = fetch
): Promise<Session> {
  const t = await tokenCall(
    c,
    { grant_type: "authorization_code", code, code_verifier: verifier, redirect_uri: redirectUri },
    fetcher
  );
  return sessionFromTokens(t);
}

export async function refreshSession(
  c: OidcConfig,
  s: Session,
  fetcher: typeof fetch = fetch
): Promise<Session> {
  const t = await tokenCall(
    c,
    { grant_type: "refresh_token", refresh_token: s.refreshToken },
    fetcher
  );
  return sessionFromTokens(t, s);
}

export async function revokeSession(c: OidcConfig, s: Session, fetcher: typeof fetch = fetch) {
  await fetcher(endpoints(c).revoke, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: c.clientId,
      token: s.refreshToken,
      token_type_hint: "refresh_token",
    }).toString(),
  }).catch(() => undefined);
}

// ---------- flows ----------

export type Flow = { state: string; verifier: string; nonce: string; returnTo: string };

/** Only same-app relative paths; anything else returns "/". */
export function safeReturnTo(raw: string | null | undefined): string {
  const v = (raw ?? "").trim();
  if (!v.startsWith("/") || v.startsWith("//") || v.startsWith("/\\")) return "/";
  if (v.startsWith("/auth/")) return "/";
  return v;
}

export async function authorizeUrl(
  c: OidcConfig,
  redirectUri: string,
  flow: Flow,
  opts: { register?: boolean; idpHint?: string; loginHint?: string; prompt?: string } = {}
): Promise<string> {
  const u = new URL(endpoints(c).authorize);
  const q = u.searchParams;
  q.set("client_id", c.clientId);
  q.set("response_type", "code");
  q.set("scope", "openid profile email");
  q.set("redirect_uri", redirectUri);
  q.set("state", flow.state);
  q.set("nonce", flow.nonce);
  q.set("code_challenge", await pkceChallenge(flow.verifier));
  q.set("code_challenge_method", "S256");
  if (opts.register) q.set("prompt", "create");
  else if (opts.prompt) q.set("prompt", opts.prompt);
  if (opts.idpHint) q.set("kc_idp_hint", opts.idpHint);
  if (opts.loginHint) q.set("login_hint", opts.loginHint);
  return u.toString();
}

export function newFlow(returnTo: string): Flow {
  return { state: randomToken(16), verifier: randomToken(48), nonce: randomToken(16), returnTo };
}

export function logoutUrl(c: OidcConfig, postLogout: string, idToken?: string): string {
  const u = new URL(endpoints(c).logout);
  u.searchParams.set("client_id", c.clientId);
  u.searchParams.set("post_logout_redirect_uri", postLogout);
  if (idToken) u.searchParams.set("id_token_hint", idToken);
  return u.toString();
}

export function appOrigin(
  c: OidcConfig,
  requestUrl: string,
  headers?: { get(n: string): string | null }
) {
  if (c.appUrl) return c.appUrl;
  const host = headers?.get("x-forwarded-host");
  if (host)
    return `${headers?.get("x-forwarded-proto") ?? "https"}://${host.split(",")[0]!.trim()}`;
  return new URL(requestUrl).origin;
}
