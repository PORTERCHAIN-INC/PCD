/**
 * Plain-language status for the merchant Connections tab.
 * One line per integration: light + reason + the one fix that resolves it.
 */
import type { MerchantApi, MerchantWebhookDeliveryRow } from "@/lib/merchants";
import type { ConnectionItem } from "@/lib/merchant-ops";

export type Light = "red" | "amber" | "green" | "off";
export type FixKind =
  | "reconnect"
  | "resume_orders"
  | "repair_setup"
  | "add_pickup"
  | "review_failed_orders"
  | "backfill"
  | "retry_failed"
  | "turn_on"
  | "rotate"
  | "retry_tracking";

export type Status = {
  light: Light;
  reason: string;
  more: string[];
  fix: { kind: FixKind; label: string; elevated?: boolean } | null;
};

/** Roles that may change merchant integrations (API module "merchants"). */
export const MERCHANTS_WRITE_ROLES = new Set([
  "super_admin",
  "admin",
  "sales",
  "sales_manager",
  "compliance",
]);
/** Freeze, disconnect, pause, repair, rotate: super admin or compliance only (server enforces too). */
export const INTEGRATIONS_ELEVATED_ROLES = new Set(["super_admin", "compliance"]);

/** Fail closed: while the profile is loading nobody gets write controls (was fail-open). */
export function canMutateIntegrations(role: string | null | undefined): boolean {
  return !!role && MERCHANTS_WRITE_ROLES.has(role.toLowerCase());
}
export function canElevateIntegrations(role: string | null | undefined): boolean {
  return !!role && INTEGRATIONS_ELEVATED_ROLES.has(role.toLowerCase());
}

const DAY = 86_400_000;
export function ago(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "never";
  const ms = now - new Date(iso).getTime();
  if (ms < 60_000) return "just now";
  if (ms < 3_600_000) return `${Math.round(ms / 60_000)} min ago`;
  if (ms < DAY) return `${Math.round(ms / 3_600_000)} h ago`;
  return `${Math.round(ms / DAY)} d ago`;
}

type Shop = NonNullable<MerchantApi["shopify_shops"]>[number];
type Partner = MerchantApi["shopify_partner"];

const FIX_LABEL: Record<string, { label: string; elevated?: boolean }> = {
  reconnect: { label: "Send reconnect link" },
  resume_orders: { label: "Resume orders", elevated: true },
  repair_setup: { label: "Repair store setup", elevated: true },
  add_pickup: { label: "Add pickup address" },
  review_failed_orders: { label: "Review orders" },
  backfill: { label: "Pull recent orders" },
  retry_tracking: { label: "Resend tracking" },
};

/** The API's shared health (same object the merchant portal renders) → this tab's Status. */
export function fromHealth(h: NonNullable<Shop["health"]>): Status {
  const fix = h.fix && FIX_LABEL[h.fix] ? { kind: h.fix as FixKind, ...FIX_LABEL[h.fix] } : null;
  if (fix?.kind === "review_failed_orders")
    fix.label = `Review ${h.orders_waiting} order${h.orders_waiting === 1 ? "" : "s"}`;
  return { light: h.light, reason: h.reason, more: h.problems.slice(1).map((p) => p.text), fix };
}

export function shopStatus(
  shop: Shop,
  partner: Partner | undefined,
  watch: ConnectionItem | undefined,
  now = Date.now()
): Status {
  if (shop.health) return fromHealth(shop.health);
  const problems: { reason: string; fix: Status["fix"] }[] = [];
  if (!shop.installed) {
    problems.push({
      reason: "Store disconnected — orders are not coming in",
      fix: { kind: "reconnect", label: "Send reconnect link" },
    });
  }
  const missing = watch?.missing_scopes ?? [];
  if (shop.installed && missing.length) {
    problems.push({
      reason: `Missing Shopify permissions (${missing.length})`,
      fix: { kind: "reconnect", label: "Send reconnect link" },
    });
  }
  if (shop.installed && shop.ingress_paused) {
    problems.push({
      reason: "New orders paused by staff",
      fix: { kind: "resume_orders", label: "Resume orders", elevated: true },
    });
  }
  const dlq = watch?.dlq_open ?? partner?.ingress_dlq_open ?? 0;
  if (dlq > 0) {
    problems.push({
      reason: `${dlq} order${dlq === 1 ? "" : "s"} couldn't be booked`,
      fix: { kind: "review_failed_orders", label: `Review ${dlq} order${dlq === 1 ? "" : "s"}` },
    });
  }
  if (shop.installed && shop.missing_pickup) {
    problems.push({
      reason: "No pickup address — orders can't be booked",
      fix: { kind: "add_pickup", label: "Add pickup address" },
    });
  }
  if (shop.installed && !shop.carrier_registered) {
    problems.push({
      reason: "Checkout shipping rates not set up",
      fix: { kind: "repair_setup", label: "Repair store setup", elevated: true },
    });
  }
  if (problems.length) {
    return {
      light: "red",
      reason: problems[0].reason,
      more: problems.slice(1).map((p) => p.reason),
      fix: problems[0].fix,
    };
  }
  const quiet = shop.last_webhook_at
    ? now - new Date(shop.last_webhook_at).getTime() > 7 * DAY
    : true;
  const warnings = [...(watch?.warnings ?? [])];
  if (quiet) {
    return {
      light: "amber",
      reason: shop.last_webhook_at
        ? `No order activity for ${ago(shop.last_webhook_at, now).replace(" ago", "")}`
        : "Connected, no orders yet",
      more: warnings,
      fix: { kind: "backfill", label: "Pull recent orders" },
    };
  }
  return {
    light: "green",
    reason: `Connected · last order ${ago(shop.last_webhook_at, now)}`,
    more: warnings,
    fix: null,
  };
}

type Key = MerchantApi["api_keys"][number];
export function keyStatus(
  key: Key,
  throttled: boolean,
  watch: ConnectionItem | undefined,
  now = Date.now()
): Status {
  const expired = !!key.expires_at && new Date(key.expires_at).getTime() <= now;
  if (!key.is_active || expired)
    return {
      light: "off",
      reason: expired ? "Retired after rotation" : "Revoked",
      more: [],
      fix: null,
    };
  if (watch?.problems.length) {
    return {
      light: "red",
      reason: watch.problems[0],
      more: watch.problems.slice(1),
      fix: { kind: "rotate", label: "Replace key", elevated: true },
    };
  }
  if (key.expires_at) {
    return {
      light: "amber",
      reason: `Old key — stops working ${new Date(key.expires_at).toLocaleDateString("en-CA")}`,
      more: [],
      fix: null,
    };
  }
  if (throttled) return { light: "amber", reason: "Hitting its rate limit", more: [], fix: null };
  return {
    light: "green",
    reason: `In use · last call ${ago(key.last_used_at, now)}`,
    more: watch?.warnings ?? [],
    fix: null,
  };
}

type Hook = MerchantApi["webhooks"][number];
export function hookStatus(
  hook: Hook,
  recent: MerchantWebhookDeliveryRow[],
  watch: ConnectionItem | undefined
): Status {
  if (!hook.is_active)
    return {
      light: "off",
      reason: "Turned off",
      more: [],
      fix: { kind: "turn_on", label: "Turn back on" },
    };
  const failed =
    watch?.failed_24h ??
    recent.filter((d) => d.webhook_id === hook.id && d.success === false).length;
  if (failed > 0) {
    return {
      light: "red",
      reason: `${failed} update${failed === 1 ? "" : "s"} failed to reach their system`,
      more: watch?.problems ?? [],
      fix: { kind: "retry_failed", label: "Resend failed" },
    };
  }
  return { light: "green", reason: "Delivering", more: watch?.warnings ?? [], fix: null };
}

export function summarize(statuses: Status[]): { light: Light; line: string } {
  const red = statuses.filter((s) => s.light === "red").length;
  const amber = statuses.filter((s) => s.light === "amber").length;
  if (!statuses.length) return { light: "off", line: "Nothing connected" };
  if (red) return { light: "red", line: `${red} need${red === 1 ? "s" : ""} fixing` };
  if (amber) return { light: "amber", line: `${amber} to keep an eye on` };
  return { light: "green", line: "All healthy" };
}

/** Booking-policy payload: unchanged fields keep their current value (cancelling no longer wipes them). */
export function policyPayload(
  current: { vehicle: string | null | undefined; pkg: string | null | undefined },
  picked: { vehicle: string; pkg: string },
  reason: string
) {
  return {
    default_vehicle_class:
      picked.vehicle === ""
        ? (current.vehicle ?? null)
        : picked.vehicle === "none"
          ? null
          : picked.vehicle,
    default_package_type:
      picked.pkg === "" ? (current.pkg ?? null) : picked.pkg === "none" ? null : picked.pkg,
    reason,
  };
}

/** Delivery-log helpers (backend rows use success/response_status; legacy rows use status/http_status). */
export function deliveryFailed(d: MerchantWebhookDeliveryRow): boolean {
  if (typeof d.success === "boolean") return !d.success;
  return d.status === "failed" || d.status === "error";
}
