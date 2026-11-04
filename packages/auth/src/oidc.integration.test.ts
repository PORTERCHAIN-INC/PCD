/**
 * Full browser-style code + PKCE flow against the THROWAWAY Keycloak (scripts/test-keycloak.sh).
 * Skipped unless PCD_TEST_KEYCLOAK_URL is set; refuses the live pch-keycloak ports.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  authorizeUrl,
  exchangeCode,
  newFlow,
  oidcConfig,
  refreshSession,
  revokeSession,
} from "./oidc/core.ts";

const BASE = (process.env.PCD_TEST_KEYCLOAK_URL ?? "").replace(/\/+$/, "");
if (BASE && /:(8180|8543)\b/.test(BASE)) throw new Error("refusing the live pch-keycloak ports");

async function admin(): Promise<string> {
  const r = await fetch(`${BASE}/realms/master/protocol/openid-connect/token`, {
    method: "POST",
    body: new URLSearchParams({
      grant_type: "password",
      client_id: "admin-cli",
      username: "admin",
      password: process.env.PCD_TEST_KEYCLOAK_ADMIN_PASSWORD ?? "test-admin-only",
    }),
  });
  return ((await r.json()) as { access_token: string }).access_token;
}

function jar() {
  const c = new Map<string, string>();
  return {
    header: () => [...c].map(([k, v]) => `${k}=${v}`).join("; "),
    take(res: Response) {
      for (const sc of res.headers.getSetCookie()) {
        const [kv] = sc.split(";");
        const i = kv!.indexOf("=");
        c.set(kv!.slice(0, i), kv!.slice(i + 1));
      }
    },
  };
}

test(
  "merchant portal: Keycloak login → code → tokens → refresh → revoke",
  { skip: !BASE },
  async () => {
    const tok = await admin();
    const h = { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" };
    const email = `web-${Date.now()}@example.test`;
    const password = `Pw-${crypto.randomUUID()}`;
    const adm = `${BASE}/admin/realms/porterchain`;
    await fetch(`${adm}/users`, {
      method: "POST",
      headers: h,
      body: JSON.stringify({
        username: email,
        email,
        firstName: "Web",
        lastName: "Merchant",
        enabled: true,
        emailVerified: true,
        credentials: [{ type: "password", value: password, temporary: false }],
      }),
    });
    const [user] = (await (
      await fetch(`${adm}/users?email=${email}&exact=true`, { headers: h })
    ).json()) as {
      id: string;
    }[];
    try {
      const cfg = oidcConfig({
        KEYCLOAK_URL: BASE,
        KEYCLOAK_CLIENT_ID: "pc-merchant-portal",
        AUTH_SESSION_SECRET: "t".repeat(40),
      })!;
      const redirect = "http://localhost:3001/auth/callback";
      const flow = newFlow("/orders");
      const j = jar();
      let res = await fetch(await authorizeUrl(cfg, redirect, flow), { redirect: "manual" });
      j.take(res);
      const html = await res.text();
      const action = /<form[^>]+id="kc-form-login"[^>]+action="([^"]+)"/.exec(html)?.[1];
      assert.ok(action, "Keycloak login form");
      res = await fetch(action.replace(/&amp;/g, "&"), {
        method: "POST",
        redirect: "manual",
        headers: { cookie: j.header(), "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email, password, credentialId: "" }),
      });
      const loc = new URL(res.headers.get("location") ?? "");
      assert.equal(`${loc.origin}${loc.pathname}`, redirect);
      assert.equal(loc.searchParams.get("state"), flow.state);
      const s = await exchangeCode(cfg, loc.searchParams.get("code")!, flow.verifier, redirect);
      assert.equal(s.user.id, user!.id);
      assert.equal(s.user.email, email);
      assert.equal(s.user.fullName, "Web Merchant");
      const r2 = await refreshSession(cfg, s);
      assert.notEqual(r2.accessToken, s.accessToken);
      await revokeSession(cfg, r2);
      await assert.rejects(refreshSession(cfg, r2));
    } finally {
      await fetch(`${adm}/users/${user!.id}`, { method: "DELETE", headers: h });
    }
  }
);
