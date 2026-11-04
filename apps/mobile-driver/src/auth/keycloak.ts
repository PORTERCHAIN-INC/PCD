/**
 * Keycloak OIDC for the mobile app (L36): Authorization Code + PKCE (S256) in the system auth
 * session (ASWebAuthenticationSession / Custom Tabs). Google and Apple go through the same
 * Keycloak broker with kc_idp_hint, so the app only ever holds Keycloak tokens. The App Review
 * account signs in on the same Keycloak page with email + password (no OTP for that role).
 * Pure functions: no React / native imports so vitest covers them.
 */

export type Env = Record<string, string | undefined>;

// Expo inlines EXPO_PUBLIC_* only for literal `process.env.X` reads, so list them here.
const BUILD_ENV: Env = {
  EXPO_PUBLIC_KEYCLOAK_URL: process.env.EXPO_PUBLIC_KEYCLOAK_URL,
  EXPO_PUBLIC_KEYCLOAK_REALM: process.env.EXPO_PUBLIC_KEYCLOAK_REALM,
  EXPO_PUBLIC_KEYCLOAK_CLIENT_ID: process.env.EXPO_PUBLIC_KEYCLOAK_CLIENT_ID,
  EXPO_PUBLIC_APPLE_SIGN_IN_ENABLED: process.env.EXPO_PUBLIC_APPLE_SIGN_IN_ENABLED,
  EXPO_PUBLIC_GOOGLE_SIGN_IN_ENABLED: process.env.EXPO_PUBLIC_GOOGLE_SIGN_IN_ENABLED,
  EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
  EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
};

/** Native Google needs the Web client id (token audience Keycloak trusts) + iOS client id. */
export function googleNativeConfig(
  env: Env = BUILD_ENV
): { webClientId: string; iosClientId?: string } | null {
  const webClientId = (env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? "").trim();
  if (!webClientId) return null;
  const ios = (env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID ?? "").trim();
  return ios ? { webClientId, iosClientId: ios } : { webClientId };
}

export const DEFAULT_CLIENT_ID = "pc-driver-app";
export const REDIRECT_URI = "porterchain-driver://auth";
const PROD_KEYCLOAK = "https://auth.porterchain.com";

export type KeycloakConfig = { url: string; realm: string; clientId: string };
export type IdpHint = "google" | "apple";
export type Tokens = {
  accessToken: string;
  refreshToken: string | null;
  idToken: string | null;
  /** epoch ms */
  expiresAt: number;
};

const on = (v: string | undefined) => (v ?? "").trim().toLowerCase() === "true";

export function keycloakConfig(env: Env = BUILD_ENV, dev = false): KeycloakConfig | null {
  const raw = (env.EXPO_PUBLIC_KEYCLOAK_URL ?? "").trim().replace(/\/$/, "");
  const url = raw || (dev ? "" : PROD_KEYCLOAK);
  if (!url) return null;
  return {
    url,
    realm: (env.EXPO_PUBLIC_KEYCLOAK_REALM ?? "").trim() || "porterchain",
    clientId: (env.EXPO_PUBLIC_KEYCLOAK_CLIENT_ID ?? "").trim() || DEFAULT_CLIENT_ID,
  };
}

/** Apple must sit next to Google at the same size (Guideline 4.8); both default on. */
export function idpEnabled(hint: IdpHint, env: Env = BUILD_ENV): boolean {
  const v =
    hint === "apple"
      ? env.EXPO_PUBLIC_APPLE_SIGN_IN_ENABLED
      : env.EXPO_PUBLIC_GOOGLE_SIGN_IN_ENABLED;
  return v == null || v.trim() === "" ? true : on(v);
}

export function endpoints(kc: KeycloakConfig) {
  const base = `${kc.url}/realms/${encodeURIComponent(kc.realm)}/protocol/openid-connect`;
  return {
    authorize: `${base}/auth`,
    token: `${base}/token`,
    logout: `${base}/logout`,
    account: `${kc.url}/realms/${encodeURIComponent(kc.realm)}/account`,
  };
}

export function authorizeUrl(
  kc: KeycloakConfig,
  p: {
    redirectUri: string;
    codeChallenge: string;
    state: string;
    nonce: string;
    idpHint?: IdpHint;
    register?: boolean;
    loginHint?: string;
  }
): string {
  const q = new URLSearchParams({
    client_id: kc.clientId,
    response_type: "code",
    scope: "openid email profile offline_access",
    redirect_uri: p.redirectUri,
    code_challenge: p.codeChallenge,
    code_challenge_method: "S256",
    state: p.state,
    nonce: p.nonce,
  });
  if (p.idpHint) q.set("kc_idp_hint", p.idpHint);
  if (p.register) q.set("prompt", "create");
  if (p.loginHint) q.set("login_hint", p.loginHint);
  return `${endpoints(kc).authorize}?${q}`;
}

export type RedirectResult = { code: string } | { error: string };

export function parseRedirect(url: string, expectedState: string): RedirectResult {
  const qs = url.includes("?") ? url.slice(url.indexOf("?") + 1).split("#")[0] : "";
  const q = new URLSearchParams(qs);
  if (q.get("error")) return { error: q.get("error") as string };
  if (q.get("state") !== expectedState) return { error: "state_mismatch" };
  const code = q.get("code");
  return code ? { code } : { error: "missing_code" };
}

type Fetch = (
  url: string,
  init: { method: string; headers: Record<string, string>; body: string }
) => Promise<{
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
}>;

function toTokens(raw: unknown, now: number, prevRefresh: string | null = null): Tokens {
  const r = raw as Record<string, unknown>;
  if (typeof r?.access_token !== "string") throw new Error("token_response_invalid");
  return {
    accessToken: r.access_token,
    refreshToken: typeof r.refresh_token === "string" ? r.refresh_token : prevRefresh,
    idToken: typeof r.id_token === "string" ? r.id_token : null,
    expiresAt: now + Math.max(0, Number(r.expires_in ?? 60)) * 1000,
  };
}

async function postForm(fetchFn: Fetch, url: string, form: Record<string, string>) {
  const res = await fetchFn(url, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(form).toString(),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = (body as { error?: string })?.error ?? `http_${res.status}`;
    throw new Error(err);
  }
  return body;
}

/** Finish the redirect: authorization code + PKCE verifier → Keycloak tokens. */
export async function exchangeCode(
  fetchFn: Fetch,
  kc: KeycloakConfig,
  p: { code: string; codeVerifier: string; redirectUri: string },
  now = Date.now()
): Promise<Tokens> {
  const body = await postForm(fetchFn, endpoints(kc).token, {
    grant_type: "authorization_code",
    client_id: kc.clientId,
    code: p.code,
    code_verifier: p.codeVerifier,
    redirect_uri: p.redirectUri,
  });
  return toTokens(body, now);
}

/**
 * Native Sign in with Apple / Google → Keycloak tokens via OAuth token exchange (external →
 * internal, RFC 8693). Keycloak validates the provider ID token against the broker config for
 * `subjectIssuer` (alias "apple" / "google") and links or creates the user like a browser login.
 */
export async function exchangeIdpToken(
  fetchFn: Fetch,
  kc: KeycloakConfig,
  p: { subjectToken: string; subjectIssuer: IdpHint | string },
  now = Date.now()
): Promise<Tokens> {
  const body = await postForm(fetchFn, endpoints(kc).token, {
    grant_type: "urn:ietf:params:oauth:grant-type:token-exchange",
    client_id: kc.clientId,
    subject_token: p.subjectToken,
    subject_token_type: "urn:ietf:params:oauth:token-type:id_token",
    subject_issuer: p.subjectIssuer,
    requested_token_type: "urn:ietf:params:oauth:token-type:refresh_token",
    scope: "openid email profile offline_access",
  });
  return toTokens(body, now);
}

export async function refreshTokens(
  fetchFn: Fetch,
  kc: KeycloakConfig,
  t: Tokens,
  now = Date.now()
): Promise<Tokens> {
  if (!t.refreshToken) throw new Error("no_refresh_token");
  const body = await postForm(fetchFn, endpoints(kc).token, {
    grant_type: "refresh_token",
    client_id: kc.clientId,
    refresh_token: t.refreshToken,
  });
  return toTokens(body, now, t.refreshToken);
}

export async function revoke(fetchFn: Fetch, kc: KeycloakConfig, t: Tokens): Promise<void> {
  if (!t.refreshToken) return;
  await postForm(fetchFn, endpoints(kc).logout, {
    client_id: kc.clientId,
    refresh_token: t.refreshToken,
  }).catch(() => undefined);
}

/** Refresh 30 s early so API calls never carry a token that expires in flight. */
export function needsRefresh(t: Tokens, now = Date.now()): boolean {
  return t.expiresAt - now < 30_000;
}

function b64urlDecode(s: string): string {
  const b = s
    .replace(/-/g, "+")
    .replace(/_/g, "/")
    .padEnd(Math.ceil(s.length / 4) * 4, "=");
  const atobFn = (globalThis as { atob?: (x: string) => string }).atob;
  return atobFn ? decodeURIComponent(escape(atobFn(b))) : "";
}

/** Read sub/email from the access token for display only (the API verifies the signature). */
export function identityFromToken(accessToken: string): {
  userId: string | null;
  email: string | null;
} {
  try {
    const payload = JSON.parse(b64urlDecode(accessToken.split(".")[1] ?? "")) as {
      sub?: string;
      email?: string;
    };
    return { userId: payload.sub ?? null, email: payload.email ?? null };
  } catch {
    return { userId: null, email: null };
  }
}

export function base64UrlFromBase64(b64: string): string {
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function authErrorCopy(code: string): string {
  if (code === "access_denied" || code === "cancel" || code === "dismiss")
    return "Sign-in was cancelled.";
  if (code === "state_mismatch") return "Sign-in expired. Try again.";
  if (code === "invalid_grant") return "Your sign-in expired. Sign in again.";
  return "Couldn’t sign in. Check your connection and try again.";
}
