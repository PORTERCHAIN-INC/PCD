import assert from "node:assert/strict";
import test from "node:test";

import { forbiddenModuleMessage, moduleLabel } from "./catalog.ts";
import {
  filterNavGroupsByModules,
  hasMerchantModule,
  MERCHANT_PALETTE_EXTRA,
  merchantPortalJob,
  requiredNavModule,
} from "./merchant-nav.ts";

test("empty modules hide every nav item", () => {
  assert.deepEqual(filterNavGroupsByModules([]), []);
  assert.deepEqual(filterNavGroupsByModules(undefined), []);
});

test("viewer modules hide billing team and integrations", () => {
  const groups = filterNavGroupsByModules(["dashboard", "orders", "tracking", "support"]);
  const hrefs = groups.flatMap((g) => g.items.map((i) => i.href));
  assert.ok(hrefs.includes("/dashboard"));
  assert.ok(hrefs.includes("/orders"));
  assert.ok(hrefs.includes("/help"));
  assert.ok(!hrefs.includes("/billing"));
  assert.ok(!hrefs.includes("/team"));
  assert.ok(!hrefs.includes("/api"));
  assert.ok(!hrefs.includes("/settings"));
  assert.ok(!hrefs.includes("/routes"));
  assert.ok(!hrefs.includes("/book"));
  assert.ok(!hrefs.includes("/reports"));
});

test("dispatcher book module shows request capacity", () => {
  const groups = filterNavGroupsByModules([
    "dashboard",
    "book",
    "routes",
    "orders",
    "tracking",
    "claims",
  ]);
  const hrefs = groups.flatMap((g) => g.items.map((i) => i.href));
  assert.ok(hrefs.includes("/book"));
  assert.ok(hrefs.includes("/routes"));
  assert.equal(
    groups.flatMap((g) => g.items).find((i) => i.href === "/book")?.label,
    "Book delivery"
  );
});

test("direct URLs resolve to the same page keys as the API", () => {
  assert.equal(requiredNavModule("/billing"), "billing");
  assert.equal(requiredNavModule("/team"), "users");
  assert.equal(requiredNavModule("/referrals"), "settings");
  assert.equal(requiredNavModule("/book"), "book");
  assert.equal(requiredNavModule("/bulk"), "bulk");
  assert.equal(requiredNavModule("/orders/abc"), "orders");
  assert.equal(hasMerchantModule(["orders"], "billing"), false);
});

test("nav has no duplicate hrefs", () => {
  const all = filterNavGroupsByModules([
    "dashboard",
    "book",
    "routes",
    "orders",
    "tracking",
    "support",
    "billing",
    "reports",
    "api_keys",
    "users",
    "settings",
  ]).flatMap((g) => g.items.map((i) => i.href));
  assert.equal(new Set(all).size, all.length);
});

test("module copy never shows internal keys", () => {
  assert.equal(moduleLabel("billing"), "Billing");
  assert.equal(forbiddenModuleMessage("users"), "Ask your owner for Manager access.");
  assert.equal(forbiddenModuleMessage("billing"), "Ask your owner for Accounting access.");
  assert.ok(!forbiddenModuleMessage("claims").includes("claims"));
  assert.ok(!moduleLabel("api_keys").includes("_"));
});

test("inbox lives on the bell + ⌘K (no duplicate nav item), gated by support", () => {
  const groups = filterNavGroupsByModules(["dashboard", "orders", "tracking", "support"]);
  assert.ok(!groups.flatMap((g) => g.items).some((i) => i.href === "/notifications"));
  assert.ok(MERCHANT_PALETTE_EXTRA.some((e) => e.href === "/notifications"));
  assert.equal(requiredNavModule("/notifications"), "support");
  assert.equal(requiredNavModule("/help"), "support");
  assert.equal(moduleLabel("support"), "Inbox");
});

test("portal job follows book vs billing vs manage", () => {
  assert.equal(
    merchantPortalJob(["dashboard", "book", "routes", "orders", "tracking", "claims"]),
    "dispatcher"
  );
  assert.equal(
    merchantPortalJob(["dashboard", "billing", "invoices", "reports", "orders"]),
    "accounting"
  );
  assert.equal(merchantPortalJob(["dashboard", "orders", "tracking", "support"]), "viewer");
  assert.equal(
    merchantPortalJob(["dashboard", "book", "billing", "users", "settings", "api_keys"]),
    "owner"
  );
});
