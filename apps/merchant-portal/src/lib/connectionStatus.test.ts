import assert from "node:assert/strict";
import test from "node:test";

import { hookRow, keyRow, merchantFix, shopRow, summary } from "./connectionStatus.ts";

const shop = {
  id: "s1",
  shop_domain: "a.myshopify.com",
  connected: true,
  installed_at: null,
  uninstalled_at: null,
  default_pickup_address_id: null,
  default_pickup: null,
  has_webhook_secret: false,
};

test("paused store reads paused (same text as admin) and points to support", () => {
  const r = shopRow({
    ...shop,
    health: {
      state: "paused",
      connected: true,
      paused: true,
      light: "red",
      reason: "New orders paused by PorterChain staff",
      fix: "resume_orders",
      problems: [
        { code: "paused", text: "New orders paused by PorterChain staff", fix: "resume_orders" },
      ],
      missing_scopes: [],
      orders_waiting: 0,
      last_order_at: null,
    },
  });
  assert.equal(r.light, "red");
  assert.equal(r.reason, "New orders paused by PorterChain staff");
  assert.deepEqual(r.fix, {
    kind: "link",
    label: "Contact support",
    href: "mailto:support@porterchain.com",
  });
});

test("staff-only fixes are not offered to merchants", () => {
  assert.equal(merchantFix("backfill", shop), null);
});

test("missing permissions → reconnect", () => {
  assert.equal(merchantFix("reconnect", shop)?.kind, "reconnect");
});

test("rotated key past its window is off", () => {
  const k = {
    id: "k",
    name: "ERP",
    key_prefix: "pk",
    scopes: [],
    environment: "production" as const,
    rate_limit_per_minute: 60,
    is_active: true,
    created_at: "",
    expires_at: "2020-01-01T00:00:00Z",
  };
  assert.equal(keyRow(k).light, "off");
});

test("failed webhook deliveries are red with a log link", () => {
  const w = {
    id: "w",
    url: "https://x.example/h",
    events: [],
    environment: "production" as const,
    is_active: true,
  };
  const d = {
    id: "d",
    webhook_id: "w",
    event_type: "e",
    response_status: 500,
    success: false,
    attempt: 1,
    error_message: null,
    duration_ms: 1,
    next_retry_at: null,
    created_at: null,
  };
  assert.equal(hookRow(w, [d]).light, "red");
});

test("summary", () => {
  assert.equal(summary([]).line, "Nothing connected yet");
});

test("go-live blocking explains a paused store and missing permissions (was 'finishing setup')", async () => {
  const { shopifyBlockingText } = await import("./shopifyStatus.ts");
  assert.match(shopifyBlockingText(["orders_paused"]) ?? "", /paused new orders/);
  assert.match(shopifyBlockingText(["scopes_missing"]) ?? "", /approve the requested permissions/);
});
