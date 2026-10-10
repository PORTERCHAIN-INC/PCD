import { describe, expect, it } from "vitest";
import {
  canMutateIntegrations,
  hookStatus,
  keyStatus,
  policyPayload,
  shopStatus,
  summarize,
} from "./merchant-connections";

const NOW = Date.parse("2026-10-09T12:00:00Z");
const shop = {
  id: "s1",
  shop_domain: "a.myshopify.com",
  installed: true,
  installed_at: null,
  last_webhook_at: "2026-10-09T10:00:00Z",
  carrier_registered: true,
  missing_pickup: false,
  ingress_paused: false,
};

describe("merchant connections status", () => {
  it("fails closed while the admin profile is loading (was fail-open)", () => {
    expect(canMutateIntegrations(undefined)).toBe(false);
    expect(canMutateIntegrations("")).toBe(false);
    expect(canMutateIntegrations("admin")).toBe(true);
    expect(canMutateIntegrations("finance")).toBe(false);
  });

  it("green shop uses real last activity, not a constant", () => {
    const s = shopStatus(shop, undefined, undefined, NOW);
    expect(s.light).toBe("green");
    expect(s.reason).toContain("2 h ago");
    expect(s.fix).toBeNull();
  });

  it("red shop: one reason, one fix, rest under more", () => {
    const s = shopStatus(
      { ...shop, ingress_paused: true, missing_pickup: true },
      { ingress_dlq_open: 2 },
      undefined,
      NOW
    );
    expect(s.light).toBe("red");
    expect(s.reason).toBe("New orders paused by staff");
    expect(s.fix?.kind).toBe("resume_orders");
    expect(s.more).toEqual([
      "2 orders couldn't be booked",
      "No pickup address — orders can't be booked",
    ]);
  });

  it("missing Shopify permissions surface as a reconnect fix", () => {
    const watch = {
      kind: "shopify" as const,
      id: "s1",
      name: "a",
      light: "red" as const,
      problems: ["x"],
      warnings: [],
      missing_scopes: ["write_orders"],
      fixes: [],
    };
    expect(shopStatus(shop, undefined, watch, NOW).fix?.kind).toBe("reconnect");
  });

  it("rotated key past its grace window is off even if is_active is still true", () => {
    const key = {
      id: "k",
      name: "ERP",
      key_prefix: "pk",
      environment: "production",
      scopes: [],
      rate_limit_per_minute: 60,
      is_active: true,
      expires_at: "2026-10-01T00:00:00Z",
      last_used_at: null,
      created_at: null,
    };
    expect(keyStatus(key, false, undefined, NOW).light).toBe("off");
  });

  it("disabled webhook offers exactly one fix: turn back on", () => {
    const s = hookStatus(
      { id: "w", url: "https://x", events: [], is_active: false, created_at: null },
      [],
      undefined
    );
    expect(s.fix?.kind).toBe("turn_on");
  });

  it("booking policy keeps current values when a field is left unchanged (cancel no longer wipes)", () => {
    expect(
      policyPayload({ vehicle: "box_16", pkg: "ltlPallet" }, { vehicle: "", pkg: "" }, "r")
    ).toEqual({
      default_vehicle_class: "box_16",
      default_package_type: "ltlPallet",
      reason: "r",
    });
    expect(
      policyPayload({ vehicle: "box_16", pkg: null }, { vehicle: "none", pkg: "looseParcel" }, "r")
        .default_vehicle_class
    ).toBeNull();
  });

  it("uses the API's shared health when present, so admin matches the merchant portal", () => {
    const s = shopStatus(
      {
        ...shop,
        health: {
          state: "paused",
          connected: true,
          paused: true,
          light: "red",
          reason: "New orders paused by PorterChain staff",
          fix: "resume_orders",
          problems: [
            {
              code: "paused",
              text: "New orders paused by PorterChain staff",
              fix: "resume_orders",
            },
            {
              code: "orders_waiting",
              text: "1 order couldn't be booked",
              fix: "review_failed_orders",
            },
          ],
          missing_scopes: [],
          orders_waiting: 1,
          last_order_at: null,
        },
      },
      undefined,
      undefined,
      NOW
    );
    expect(s).toEqual({
      light: "red",
      reason: "New orders paused by PorterChain staff",
      more: ["1 order couldn't be booked"],
      fix: { kind: "resume_orders", label: "Resume orders", elevated: true },
    });
  });

  it("summary line", () => {
    expect(summarize([]).line).toBe("Nothing connected");
    expect(summarize([{ light: "red", reason: "", more: [], fix: null }]).line).toBe(
      "1 needs fixing"
    );
  });
});
