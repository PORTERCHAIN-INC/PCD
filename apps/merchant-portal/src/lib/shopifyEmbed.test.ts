import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { APP_BRIDGE_SRC, shopifyApiKey } from "./shopifyEmbed.ts";

test("App Bridge loads from Shopify's CDN", () => {
  assert.equal(APP_BRIDGE_SRC, "https://cdn.shopify.com/shopifycloud/app-bridge.js");
});

test("api key is read at request time from SHOPIFY_API_KEY", () => {
  process.env.SHOPIFY_API_KEY = " abc123 ";
  assert.equal(shopifyApiKey(), "abc123");
});

test("prod compose passes SHOPIFY_API_KEY to the merchant portal", () => {
  const compose = readFileSync(
    new URL("../../../../infrastructure/deploy/docker-compose.prod.yml", import.meta.url),
    "utf8"
  );
  const merchant = compose.slice(compose.indexOf("\n  merchant:"), compose.indexOf("\n  driver:"));
  assert.match(merchant, /SHOPIFY_API_KEY: \$\{SHOPIFY_API_KEY:-\}/);
  assert.doesNotMatch(merchant, /SHOPIFY_API_SECRET/);
});
