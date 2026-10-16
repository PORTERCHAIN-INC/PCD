/** Pure display helpers for the customer app. No react-native imports (unit tested). */
import type { CustomerOrder, QuoteLine } from "./api";

export type Tone = "info" | "progress" | "success" | "danger" | "neutral";

/** 5-step journey shown on Track and on the Home hero. */
export const JOURNEY = ["Booked", "Driver assigned", "Picked up", "On the way", "Delivered"];

const STATES: Record<string, { label: string; tone: Tone; step: number }> = {
  BOOKED: { label: "Booked", tone: "info", step: 0 },
  DISPATCH_READY: { label: "Finding a driver", tone: "info", step: 0 },
  DRIVER_ASSIGNED: { label: "Driver assigned", tone: "progress", step: 1 },
  DRIVER_ACCEPTED: { label: "Driver assigned", tone: "progress", step: 1 },
  DRIVER_REJECTED: { label: "Finding a driver", tone: "info", step: 0 },
  DRIVER_EN_ROUTE: { label: "Driver heading to pickup", tone: "progress", step: 1 },
  AT_PICKUP: { label: "Driver at pickup", tone: "progress", step: 1 },
  PICKED_UP: { label: "Picked up", tone: "progress", step: 2 },
  IN_TRANSIT: { label: "On the way", tone: "progress", step: 3 },
  AT_DESTINATION: { label: "Arriving now", tone: "progress", step: 3 },
  DELIVERED: { label: "Delivered", tone: "success", step: 4 },
  POD_COMPLETED: { label: "Delivered", tone: "success", step: 4 },
  INVOICED: { label: "Delivered", tone: "success", step: 4 },
  CLOSED: { label: "Completed", tone: "success", step: 4 },
  CANCELLED: { label: "Cancelled", tone: "neutral", step: -1 },
  FAILED: { label: "Delivery problem", tone: "danger", step: -1 },
};

/** Human label, colour tone and journey step for an order state (any casing). */
export function orderStatus(state: string | null | undefined): {
  label: string;
  tone: Tone;
  step: number;
} {
  const key = (state ?? "").trim().toUpperCase();
  const hit = STATES[key];
  if (hit) return hit;
  const words = key.toLowerCase().replace(/_/g, " ").trim();
  return {
    label: words ? words[0]!.toUpperCase() + words.slice(1) : "Unknown",
    tone: "neutral",
    step: -1,
  };
}

export function isActiveState(state: string | null | undefined): boolean {
  const s = orderStatus(state);
  return s.step >= 0 && s.step < 4;
}

/** Payment status ("succeeded", "requires_payment_method", ...) to label + tone. */
export function paymentStatus(status: string): { label: string; tone: Tone } {
  const s = status.toLowerCase();
  if (s === "succeeded" || s === "paid") return { label: "Paid", tone: "success" };
  if (s === "refunded") return { label: "Refunded", tone: "neutral" };
  if (s.includes("fail") || s === "canceled" || s === "requires_payment_method")
    return { label: "Payment failed", tone: "danger" };
  return { label: "Pending", tone: "info" };
}

export function formatMoney(cents: number, currency = "CAD"): string {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency }).format(cents / 100);
}

/** First line of an address ("123 King St W, Toronto, ON ..." -> "123 King St W"). */
export function shortAddress(formatted: string | null | undefined): string {
  return (formatted ?? "").split(",")[0]!.trim();
}

/** "Today", "Yesterday", or "Mon, Oct 12" in Toronto time. */
export function friendlyDate(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const fmt = (x: Date) => x.toLocaleDateString("en-CA", { timeZone: "America/Toronto" });
  if (fmt(d) === fmt(now)) return "Today";
  if (fmt(d) === fmt(new Date(now.getTime() - 86_400_000))) return "Yesterday";
  return d.toLocaleDateString("en-CA", {
    timeZone: "America/Toronto",
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export type BookAgain = {
  order_id: string;
  from: string;
  to: string;
  tracking_number: string;
};

/**
 * Distinct recent routes (pickup -> drop-off) for one-tap "Book again", newest first.
 * Orders without both addresses are skipped.
 */
export function bookAgainRoutes(orders: CustomerOrder[], max = 3): BookAgain[] {
  const seen = new Set<string>();
  const out: BookAgain[] = [];
  for (const order of orders) {
    const from = order.pickup?.formatted?.trim();
    const to = order.dropoff?.formatted?.trim();
    if (!from || !to) continue;
    const key = `${from.toLowerCase()}→${to.toLowerCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      order_id: order.order_id,
      from: shortAddress(from),
      to: shortAddress(to),
      tracking_number: order.tracking_number,
    });
    if (out.length >= max) break;
  }
  return out;
}

export type PriceSummary = {
  lines: QuoteLine[];
  tax: QuoteLine[];
  total_cents: number;
  /** True when the API listed tax as its own line; otherwise the total includes HST. */
  taxItemised: boolean;
};

const TAX = /\b(hst|gst|pst|qst|tax)\b/i;

/**
 * Split the API's pricing breakdown into charges and tax lines. The total is
 * always the API's amount: the app never recomputes a price.
 */
export function priceSummary(breakdown: QuoteLine[], totalCents: number): PriceSummary {
  const tax = breakdown.filter((l) => TAX.test(l.code) || TAX.test(l.label));
  const lines = breakdown.filter((l) => !tax.includes(l));
  return { lines, tax, total_cents: totalCents, taxItemised: tax.length > 0 };
}

/** "Expires in 12 min" / "Expired" for a quote expiry timestamp. */
export function expiresIn(iso: string, now = new Date()): string {
  const ms = new Date(iso).getTime() - now.getTime();
  if (!Number.isFinite(ms)) return "";
  if (ms <= 0) return "Quote expired";
  const min = Math.round(ms / 60_000);
  if (min < 60) return `Price held for ${Math.max(1, min)} min`;
  const h = Math.round(min / 60);
  return `Price held for ${h} h`;
}

/** Network-ish failures that should show the offline banner rather than an error. */
export function isOfflineError(message: string): boolean {
  return /network request failed|aborted|abort|timeout|offline|failed to fetch/i.test(message);
}
