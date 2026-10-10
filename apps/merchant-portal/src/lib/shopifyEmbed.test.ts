import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { APP_BRIDGE_SRC, embeddedAppHtml, shopifyApiKey } from "./shopifyEmbed.ts";

const html = embeddedAppHtml({
  apiKey: "85df9348abc",
  apiUrl: "https://api.porterchain.com",
  portalUrl: "https://merchant.porterchain.com",
});

test("api-key meta then App Bridge are the first things in <head>", () => {
  const head = html.slice(html.indexOf("<head>") + 6, html.indexOf("</head>")).trim();
  assert.ok(head.startsWith('<meta name="shopify-api-key" content="85df9348abc" />'));
  const firstScript = head.match(/<script[^>]*>/)?.[0];
  assert.equal(firstScript, `<script src="${APP_BRIDGE_SRC}">`);
  assert.doesNotMatch(firstScript ?? "", /async|defer|type=/);
});

test("page states the 150 km service area and posts the session token", () => {
  assert.match(html, /Toronto and up to 150 km/);
  assert.match(html, /\/v1\/integrations\/shopify\/session/);
});

test("api key is read at request time from SHOPIFY_API_KEY", () => {
  process.env.SHOPIFY_API_KEY = " abc123 ";
  assert.equal(shopifyApiKey(), "abc123");
});

test("prod compose passes SHOPIFY_API_KEY (not the secret) to the merchant portal", () => {
  const compose = readFileSync(
    new URL("../../../../infrastructure/deploy/docker-compose.prod.yml", import.meta.url),
    "utf8"
  );
  const merchant = compose.slice(compose.indexOf("\n  merchant:"), compose.indexOf("\n  driver:"));
  assert.match(merchant, /SHOPIFY_API_KEY: \$\{SHOPIFY_API_KEY:-\}/);
  assert.doesNotMatch(merchant, /SHOPIFY_API_SECRET/);
});

test("Shipping button uses App Bridge admin navigation, no store placeholder", () => {
  assert.match(html, /shopify:\/\/admin\/settings\/shipping/);
  assert.doesNotMatch(html, /__SHOP__|__shop__|admin\.shopify\.com\/store/);
  assert.match(html, /open\(SHIP,"_top"\)/);
});

test("steps cover the Markets layout first, old zones as fallback", () => {
  assert.ok(html.indexOf("Shipping has moved to Markets") < html.indexOf("Older admin"));
  assert.match(html, /PorterChain \(via app\)/);
});

test("4-click flag off adds nothing; on adds Confirm pickup + Go live", () => {
  const on = embeddedAppHtml({
    apiKey: "k",
    apiUrl: "https://a",
    portalUrl: "https://p",
    fourClick: true,
  });
  const off = embeddedAppHtml({ apiKey: "k", apiUrl: "https://a", portalUrl: "https://p" });
  assert.doesNotMatch(off, /__pcOnboard|Go live/);
  assert.match(on, /Confirm pickup/);
  assert.match(on, /Go live/);
  assert.ok(on.indexOf("__pcOnboard=") < on.lastIndexOf("window.__pcOnboard(s,render)"));
});
