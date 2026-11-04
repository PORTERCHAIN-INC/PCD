/**
 * Persona sign-in / sign-out like a human: fresh context, type into the real Keycloak form at
 * the LAN address, pass the Mailpit email code if asked, land on the right dashboard, then
 * Sign out must clear both the app cookie and the Keycloak SSO session.
 *
 *   LS_HOST=http://192.168.2.103 pnpm exec playwright test -c e2e-local-stack  (from website/)
 * Credentials: ~/.pcd-local-stack/demo-logins.env and qa-admin.env (never printed).
 */
import { test, expect, type Page } from "@playwright/test";
import fs from "fs";
import crypto from "crypto";

const H = process.env.LS_HOST ?? "http://192.168.2.103";
const KC = `${H}:18280/realms/porterchain`;
const MP = process.env.MAILPIT_URL ?? "http://127.0.0.1:58026";
const DIR = `${process.env.HOME}/.pcd-local-stack`;
const env = (f: string): Record<string, string> =>
  fs.existsSync(`${DIR}/${f}`)
    ? Object.fromEntries(
        fs
          .readFileSync(`${DIR}/${f}`, "utf8")
          .split("\n")
          .filter((l) => l.includes("=") && !l.startsWith("#"))
          .map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1)])
      )
    : {};
const D = env("demo-logins.env");
const A = env("qa-admin.env");

function totp(sec: string) {
  const a = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const c of sec.replace(/=|\s/g, "").toUpperCase())
    bits += a.indexOf(c).toString(2).padStart(5, "0");
  const k = Buffer.from(bits.match(/.{8}/g)!.map((x) => parseInt(x, 2)));
  const t = Buffer.alloc(8);
  t.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const h = crypto.createHmac("sha1", k).update(t).digest();
  const o = h[19] & 15;
  return String((h.readUInt32BE(o) & 0x7fffffff) % 1e6).padStart(6, "0");
}

async function emailCode(p: Page, email: string, since: number) {
  if (
    (await p
      .locator("body")
      .getAttribute("data-page-id")
      .catch(() => null)) !== "login-login-email-otp"
  )
    return;
  for (let i = 0; i < 30; i++) {
    const r = await (
      await fetch(
        `${MP}/api/v1/search?query=${encodeURIComponent(`to:${email} subject:code`)}&limit=1`
      )
    ).json();
    const m = r.messages?.[0];
    if (m && Date.parse(m.Created) >= since - 2000) {
      const code = ((await (await fetch(`${MP}/api/v1/message/${m.ID}`)).json()).Text.match(
        /\b\d{6}\b/
      ) || [])[0];
      if (code) {
        await p.fill("#email-otp", code);
        await p.click("#kc-login");
        return;
      }
    }
    await p.waitForTimeout(500);
  }
  throw new Error(
    "email code requested but none arrived in Mailpit (Keycloak email_otp_issuance_limit: 5 codes per user per 15 min; wait and rerun)"
  );
}

async function keycloakForm(p: Page, email: string, password: string, totpSecret?: string) {
  await p.waitForURL(/:18280\//, { timeout: 20_000 });
  await p.locator("#username").fill(email);
  if (await p.locator("#password").count()) await p.locator("#password").fill(password);
  const since = Date.now();
  await p.click("#kc-login");
  await p.waitForLoadState("networkidle").catch(() => {});
  if (await p.locator("#password").count()) {
    await p.locator("#password").fill(password);
    await p.click("#kc-login");
    await p.waitForLoadState("networkidle").catch(() => {});
  }
  if (totpSecret && (await p.locator("#otp").count())) {
    await p.fill("#otp", totp(totpSecret));
    await p.click("#kc-login");
  }
  await emailCode(p, email, since);
}

/** Keycloak SSO session gone? prompt=none must answer login_required. */
async function expectKeycloakSignedOut(p: Page, appPort: number) {
  const u = `${KC}/protocol/openid-connect/auth?client_id=pc-website&response_type=code&scope=openid&prompt=none&state=s1&code_challenge_method=S256&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&redirect_uri=${encodeURIComponent(`${H}:53005/auth/callback`)}`;
  const r = await p.request.get(u, { maxRedirects: 0 });
  expect(
    r.headers()["location"] ?? "",
    `Keycloak session should be cleared after sign-out on :${appPort}`
  ).toContain("error=login_required");
}

async function signOut(p: Page, port: number) {
  const btn = p
    .getByRole("button", { name: /sign out|log out/i })
    .or(p.getByRole("link", { name: /sign out|log out/i }))
    .first();
  await p.waitForLoadState("networkidle").catch(() => {}); // let client-side redirects settle
  if (await btn.isVisible().catch(() => false)) await btn.click();
  else
    await p.goto(`${H}:${port}/auth/logout`).catch(async () => p.goto(`${H}:${port}/auth/logout`));
  await p.waitForLoadState("networkidle").catch(() => {});
  // App cookie cleared: a protected page sends us back to the sign-in form.
  await p.goto(`${H}:${port}/`);
  await expect(p).toHaveURL(/:18280\/|sign-in|login/, { timeout: 20_000 });
  await expectKeycloakSignedOut(p, port);
}

const personas = [
  {
    app: "merchant",
    port: 53001,
    email: D.MERCHANT_EMAIL,
    pw: D.MERCHANT_PASSWORD,
    land: /:53001\/(dashboard|onboarding)/,
    bad: /Session error|Could not load/i,
  },
  {
    app: "driver",
    port: 53003,
    email: D.DRIVER_EMAIL,
    pw: D.DRIVER_PASSWORD,
    land: /:53003\/(dashboard|onboarding)/,
    bad: /not_provisioned|could not load/i,
  },
  {
    app: "customer",
    port: 53004,
    email: D.CUSTOMER_EMAIL,
    pw: D.CUSTOMER_PASSWORD,
    land: /:53004\/(send|orders|dashboard)/,
    bad: /could not load/i,
  },
];

for (const c of personas) {
  test(`${c.app} signs in through the form and signs out of app + Keycloak`, async ({
    browser,
  }) => {
    test.skip(!c.email, "demo-logins.env missing");
    const ctx = await browser.newContext();
    const p = await ctx.newPage();
    await p.goto(`${H}:${c.port}/`);
    await keycloakForm(p, c.email, c.pw);
    await expect(p).toHaveURL(c.land, { timeout: 30_000 });
    await p.waitForLoadState("networkidle").catch(() => {});
    await expect(p.locator("body")).not.toContainText(c.bad, { timeout: 5_000 });
    await expect(p.locator("h1").first()).toBeVisible();
    await signOut(p, c.port);
    await ctx.close();
  });
}

test("website Sign in link reaches Keycloak and lands in the customer app", async ({ browser }) => {
  const ctx = await browser.newContext();
  const p = await ctx.newPage();
  await p.goto(`${H}:53005/en`);
  await p
    .getByRole("link", { name: /^sign in$/i })
    .first()
    .click();
  await keycloakForm(p, D.CUSTOMER_EMAIL, D.CUSTOMER_PASSWORD);
  await expect(p).toHaveURL(/:53004\//, { timeout: 30_000 });
  await expect(p.locator("body")).not.toContainText(/could not load/i);
  await signOut(p, 53004);
  await ctx.close();
});

test("admin signs in (password + TOTP) and lands on Today", async ({ browser }) => {
  test.skip(!A.QA_ADMIN_TOTP_SECRET, "qa-admin.env missing");
  const ctx = await browser.newContext();
  const p = await ctx.newPage();
  await p.goto(`${H}:53002/`);
  await keycloakForm(p, A.QA_ADMIN_EMAIL, A.QA_ADMIN_PASSWORD, A.QA_ADMIN_TOTP_SECRET);
  await expect(p).toHaveURL(/:53002\/today/, { timeout: 30_000 });
  // An admin SSO session must not silently sign the browser into a persona app.
  await p.goto(`${H}:53004/`);
  await expect(p).toHaveURL(/:18280\//, { timeout: 20_000 });
  // Keycloak asks to re-authenticate (password form), never auto-signs in.
  await expect(p.locator("#password, #username").first()).toBeVisible();
  await expect(p).not.toHaveURL(/:53004\//);
  await ctx.close();
});

test("wrong-persona stuck state offers a Sign out that clears app + Keycloak", async ({
  browser,
}) => {
  const ctx = await browser.newContext();
  const p = await ctx.newPage();
  await p.goto(`${H}:53003/`); // driver app, merchant credentials (spreads email-code rate limit)
  await keycloakForm(p, D.MERCHANT_EMAIL, D.MERCHANT_PASSWORD);
  await p.waitForLoadState("networkidle").catch(() => {});
  await p.waitForTimeout(2000);
  const so = p
    .getByRole("link", { name: /sign out/i })
    .or(p.getByRole("button", { name: /sign out/i }))
    .first();
  await expect(so).toBeVisible({ timeout: 20_000 });
  await signOut(p, 53003);
  await ctx.close();
});
