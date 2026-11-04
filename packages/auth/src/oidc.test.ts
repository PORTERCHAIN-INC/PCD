import assert from "node:assert/strict";
import { test } from "node:test";
import {
  authorizeUrl,
  b64url,
  flowCookieName,
  sessionCookieName,
  chunkCookies,
  decodeJwt,
  needsRefresh,
  newFlow,
  oidcConfig,
  pkceChallenge,
  readChunks,
  safeReturnTo,
  seal,
  sessionFromTokens,
  unseal,
  exchangeCode,
  refreshSession,
  logoutUrl,
} from "./oidc/core.ts";

const env = {
  KEYCLOAK_URL: "https://auth.porterchain.com/",
  KEYCLOAK_CLIENT_ID: "pc-merchant-portal",
  AUTH_SESSION_SECRET: "x".repeat(40),
};
const cfg = oidcConfig(env)!;

function jwt(payload: Record<string, unknown>) {
  const enc = (o: unknown) => b64url(new TextEncoder().encode(JSON.stringify(o)));
  return `${enc({ alg: "none" })}.${enc(payload)}.sig`;
}

test("config requires url, client and a 32+ char secret", () => {
  assert.equal(oidcConfig({ ...env, AUTH_SESSION_SECRET: "short" }), null);
  assert.equal(oidcConfig({ ...env, KEYCLOAK_CLIENT_ID: "" }), null);
  assert.equal(cfg.url, "https://auth.porterchain.com");
  assert.equal(cfg.realm, "porterchain");
  assert.equal(cfg.internalUrl, cfg.url);
});

test("PKCE S256 matches RFC 7636 appendix B", async () => {
  assert.equal(
    await pkceChallenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"),
    "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
  );
});

test("authorize url carries PKCE, state, nonce and hints", async () => {
  const f = newFlow("/orders");
  const u = new URL(
    await authorizeUrl(cfg, "https://m.example/auth/callback", f, {
      register: true,
      idpHint: "google",
    })
  );
  assert.equal(u.pathname, "/realms/porterchain/protocol/openid-connect/auth");
  assert.equal(u.searchParams.get("code_challenge_method"), "S256");
  assert.equal(u.searchParams.get("state"), f.state);
  assert.equal(u.searchParams.get("prompt"), "create");
  assert.equal(u.searchParams.get("kc_idp_hint"), "google");
  assert.equal(u.searchParams.get("client_id"), "pc-merchant-portal");
});

test("seal/unseal round-trips and rejects tampering or the wrong secret", async () => {
  const s = await seal({ a: 1 }, cfg.secret);
  assert.deepEqual(await unseal(s, cfg.secret), { a: 1 });
  assert.equal(await unseal(s, "y".repeat(40)), null);
  assert.equal(await unseal(`${s.slice(0, -2)}AA`, cfg.secret), null);
});

test("cookies chunk and reassemble; unused chunks are cleared", () => {
  const big = "a".repeat(9000);
  const specs = chunkCookies("pc_session", big, 100);
  const jar = new Map(specs.filter((s) => s.maxAge).map((s) => [s.name, { value: s.value }]));
  assert.equal(jar.size, 3);
  assert.equal(readChunks({ get: (n) => jar.get(n) }, "pc_session"), big);
  assert.ok(specs.some((s) => s.name === "pc_session.5" && s.maxAge === 0));
});

test("return_to only allows same-app relative paths", () => {
  assert.equal(safeReturnTo("/orders?x=1"), "/orders?x=1");
  for (const bad of ["https://evil.test", "//evil.test", "/\\evil", "/auth/login", "", null]) {
    assert.equal(safeReturnTo(bad), "/");
  }
});

test("session from tokens: user claims, expiry and refresh window", () => {
  const now = Date.now();
  const exp = Math.floor(now / 1000) + 300;
  const at = jwt({ sub: "u1", exp, email: "a@b.test", pc_roles: ["merchant_owner"] });
  const id = jwt({
    sub: "u1",
    name: "A B",
    given_name: "A",
    email: "a@b.test",
    email_verified: true,
  });
  const s = sessionFromTokens({ access_token: at, refresh_token: "r", id_token: id });
  assert.equal(s.user.id, "u1");
  assert.equal(s.user.fullName, "A B");
  assert.deepEqual(s.user.roles, ["merchant_owner"]);
  assert.equal(s.expiresAt, exp);
  assert.equal(needsRefresh(s, now), false);
  assert.equal(needsRefresh(s, now + 250_000), true);
  assert.equal(decodeJwt("garbage").sub, undefined);
});

test("code exchange and refresh post the right grants to the internal token endpoint", async () => {
  const calls: { url: string; body: URLSearchParams }[] = [];
  const at = jwt({ sub: "u1", exp: Math.floor(Date.now() / 1000) + 300 });
  const fake = (async (url: string, init: RequestInit) => {
    calls.push({ url, body: new URLSearchParams(String(init.body)) });
    return new Response(JSON.stringify({ access_token: at, refresh_token: "r2" }), { status: 200 });
  }) as unknown as typeof fetch;
  const c = { ...cfg, internalUrl: "http://keycloak:8080" };
  const s = await exchangeCode(c, "code1", "ver", "https://m/auth/callback", fake);
  assert.equal(
    calls[0]!.url,
    "http://keycloak:8080/realms/porterchain/protocol/openid-connect/token"
  );
  assert.equal(calls[0]!.body.get("grant_type"), "authorization_code");
  assert.equal(calls[0]!.body.get("code_verifier"), "ver");
  const r = await refreshSession(c, s, fake);
  assert.equal(calls[1]!.body.get("grant_type"), "refresh_token");
  assert.equal(r.refreshToken, "r2");
  const bad = (async () =>
    new Response(JSON.stringify({ error: "invalid_grant" }), {
      status: 400,
    })) as unknown as typeof fetch;
  await assert.rejects(refreshSession(c, s, bad), /invalid_grant/);
});

test("logout url ends the Keycloak session and returns to the app", () => {
  const u = new URL(logoutUrl(cfg, "https://m.example/sign-in", "idt"));
  assert.equal(u.searchParams.get("post_logout_redirect_uri"), "https://m.example/sign-in");
  assert.equal(u.searchParams.get("id_token_hint"), "idt");
});

test("session cookie name is per app when AUTH_COOKIE_NAME is set (same host, different ports)", () => {
  assert.equal(sessionCookieName({}), "pc_session");
  assert.equal(flowCookieName({}), "pc_oidc_flow");
  assert.equal(
    sessionCookieName({ AUTH_COOKIE_NAME: "pc_session_customer" }),
    "pc_session_customer"
  );
  assert.equal(
    flowCookieName({ AUTH_COOKIE_NAME: "pc_session_customer" }),
    "pc_session_customer_flow"
  );
  assert.equal(sessionCookieName({ AUTH_COOKIE_NAME: "bad name;" }), "pc_session");
});
