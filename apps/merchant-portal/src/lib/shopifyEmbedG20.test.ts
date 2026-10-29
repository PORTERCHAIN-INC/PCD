import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { embeddedAppHtml } from "./shopifyEmbed.ts";

// G20 (doc 76 §10, A-SHR-01/06): nothing in the embedded flow asks for login, OTP or CAPTCHA.
const g20 = embeddedAppHtml({
  apiKey: "k",
  apiUrl: "https://a",
  portalUrl: "https://p",
  fourClick: true,
  autoProvision: true,
});

test("A-SHR-01: no sign-in, Clerk, OTP or CAPTCHA anywhere in the embedded page", () => {
  assert.doesNotMatch(
    g20,
    /clerk|captcha|turnstile|one-time code|verification code|\/sign-in|\/sign-up/i
  );
  assert.doesNotMatch(g20, /sign in to the PorterChain portal/i);
});

test("auto-provision: an unlinked store renders as ready in the iframe, no new-tab link step", () => {
  assert.match(g20, /var AUTO=true/);
  assert.match(g20, /is ready\. No sign-up or login is needed/);
  const legacy = embeddedAppHtml({ apiKey: "k", apiUrl: "https://a", portalUrl: "https://p" });
  assert.match(legacy, /var AUTO=false/);
});

test("route defaults four-click and auto-provision ON, env 'false' turns each off", () => {
  const src = readFileSync(new URL("../app/shopify-app/route.ts", import.meta.url), "utf8");
  assert.match(src, /SHOPIFY_FOUR_CLICK_ONBOARDING_ENABLED !== "false"/);
  assert.match(src, /SHOPIFY_EMBEDDED_AUTO_PROVISION_ENABLED !== "false"/);
});
