/**
 * One-line connection status for the merchant portal, matching the admin Connections tab.
 * Shopify rows come straight from the API's shared health, so a paused store reads
 * "paused" here, in admin and in the watchdog.
 */
import type {
  ApiKeyRecord,
  ShopifyShopConnection,
  WebhookDelivery,
  WebhookRecord,
} from "@/lib/integrations";

export type Light = "red" | "amber" | "green" | "off";
export type MerchantFix =
  | { kind: "reconnect"; label: string; shop: string }
  | { kind: "finish_setup"; label: string; shopId: string }
  | { kind: "link"; label: string; href: string };

export type Row = {
  id: string;
  group: "shopify" | "keys" | "webhooks";
  name: string;
  light: Light;
  reason: string;
  more: string[];
  fix: MerchantFix | null;
};

export const SUPPORT_MAIL = "mailto:support@porterchain.com";

/** What the merchant themself can do about each shared fix code. */
export function merchantFix(code: string | null, shop: ShopifyShopConnection): MerchantFix | null {
  switch (code) {
    case "reconnect":
      return { kind: "reconnect", label: "Reconnect store", shop: shop.shop_domain };
    case "repair_setup":
      return { kind: "finish_setup", label: "Finish setup", shopId: shop.id };
    case "add_pickup":
      return { kind: "link", label: "Add pickup address", href: "/settings?tab=locations" };
    case "resume_orders":
    case "review_failed_orders":
    case "retry_tracking":
      return { kind: "link", label: "Contact support", href: SUPPORT_MAIL };
    default:
      return null; // backfill etc. are staff-only
  }
}

export function shopRow(shop: ShopifyShopConnection): Row {
  const h = shop.health;
  if (!h) {
    return {
      id: shop.id,
      group: "shopify",
      name: shop.shop_domain,
      light: shop.connected ? "green" : "red",
      reason: shop.connected ? "Connected" : "Store disconnected",
      more: [],
      fix: shop.connected ? null : merchantFix("reconnect", shop),
    };
  }
  return {
    id: shop.id,
    group: "shopify",
    name: shop.shop_domain,
    light: h.light,
    reason: h.reason,
    more: h.problems.slice(1).map((p) => p.text),
    fix: merchantFix(h.fix, shop),
  };
}

export function keyRow(k: ApiKeyRecord, now = Date.now()): Row {
  const expired = !!k.expires_at && new Date(k.expires_at).getTime() <= now;
  const name = `${k.name} · ${k.environment === "sandbox" ? "Test" : "Live"}`;
  if (!k.is_active || expired)
    return {
      id: k.id,
      group: "keys",
      name,
      light: "off",
      reason: expired ? "Retired after replacement" : "Revoked",
      more: [],
      fix: null,
    };
  if (k.expires_at)
    return {
      id: k.id,
      group: "keys",
      name,
      light: "amber",
      reason: `Old key — stops working ${new Date(k.expires_at).toLocaleDateString("en-CA")}`,
      more: [],
      fix: { kind: "link", label: "Switch to the new key", href: "/api?tab=keys" },
    };
  return { id: k.id, group: "keys", name, light: "green", reason: "Active", more: [], fix: null };
}

export function hookRow(w: WebhookRecord, logs: WebhookDelivery[]): Row {
  const name = w.url.replace(/^https?:\/\//, "");
  if (!w.is_active)
    return {
      id: w.id,
      group: "webhooks",
      name,
      light: "off",
      reason: "Turned off",
      more: [],
      fix: null,
    };
  const failed = logs.filter((d) => d.webhook_id === w.id && !d.success).length;
  if (failed) {
    return {
      id: w.id,
      group: "webhooks",
      name,
      light: "red",
      reason: `${failed} update${failed === 1 ? "" : "s"} didn't reach your system`,
      more: [],
      fix: { kind: "link", label: "See delivery log", href: "/api?tab=logs" },
    };
  }
  return {
    id: w.id,
    group: "webhooks",
    name,
    light: "green",
    reason: "Delivering",
    more: [],
    fix: null,
  };
}

export function summary(rows: Row[]): { light: Light; line: string } {
  const live = rows.filter((r) => r.light !== "off");
  const red = live.filter((r) => r.light === "red").length;
  const amber = live.filter((r) => r.light === "amber").length;
  if (!live.length) return { light: "off", line: "Nothing connected yet" };
  if (red) return { light: "red", line: `${red} need${red === 1 ? "s" : ""} your attention` };
  if (amber) return { light: "amber", line: `${amber} to keep an eye on` };
  return { light: "green", line: "Everything is connected" };
}
