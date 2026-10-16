import { describe, expect, it } from "vitest";
import {
  bookAgainRoutes,
  expiresIn,
  friendlyDate,
  isActiveState,
  isOfflineError,
  orderStatus,
  paymentStatus,
  priceSummary,
  shortAddress,
} from "./format";

describe("orderStatus", () => {
  it("maps API states to customer words and journey steps", () => {
    expect(orderStatus("IN_TRANSIT")).toEqual({ label: "On the way", tone: "progress", step: 3 });
    expect(orderStatus("delivered").tone).toBe("success");
    expect(orderStatus("CANCELLED").step).toBe(-1);
  });
  it("humanises unknown states instead of showing raw codes", () => {
    expect(orderStatus("ON_HOLD").label).toBe("On hold");
    expect(orderStatus(undefined).label).toBe("Unknown");
  });
  it("knows which shipments are still moving", () => {
    expect(isActiveState("PICKED_UP")).toBe(true);
    expect(isActiveState("DELIVERED")).toBe(false);
    expect(isActiveState("FAILED")).toBe(false);
  });
});

describe("paymentStatus", () => {
  it("labels Stripe statuses", () => {
    expect(paymentStatus("succeeded")).toEqual({ label: "Paid", tone: "success" });
    expect(paymentStatus("requires_payment_method").tone).toBe("danger");
    expect(paymentStatus("processing").label).toBe("Pending");
  });
});

describe("priceSummary", () => {
  const lines = [
    { code: "base", label: "Base fare", amount_cents: 3900 },
    { code: "distance", label: "Distance", amount_cents: 3600 },
    { code: "hst", label: "HST 13%", amount_cents: 975 },
  ];
  it("separates HST from charges and keeps the API total", () => {
    const s = priceSummary(lines, 8475);
    expect(s.lines.map((l) => l.code)).toEqual(["base", "distance"]);
    expect(s.tax.map((l) => l.code)).toEqual(["hst"]);
    expect(s.total_cents).toBe(8475);
    expect(s.taxItemised).toBe(true);
  });
  it("flags a tax-inclusive total when no tax line is sent", () => {
    const s = priceSummary(lines.slice(0, 2), 8475);
    expect(s.taxItemised).toBe(false);
    expect(s.total_cents).toBe(8475);
  });
  it("does not treat words containing 'tax' substrings loosely", () => {
    expect(priceSummary([{ code: "taxi_fee", label: "Taxi", amount_cents: 1 }], 1).tax).toEqual([]);
  });
});

describe("bookAgainRoutes", () => {
  const order = (id: string, from: string, to: string) => ({
    order_id: id,
    tracking_number: `T-${id}`,
    state: "DELIVERED",
    pickup: { formatted: from },
    dropoff: { formatted: to },
  });
  it("returns distinct recent routes, newest first", () => {
    const routes = bookAgainRoutes([
      order("1", "8450 Lawson Rd, Milton", "100 King St W, Toronto"),
      order("2", "8450 Lawson Rd, Milton", "100 King St W, Toronto"),
      order("3", "100 King St W, Toronto", "1 City Centre Dr, Mississauga"),
      { ...order("4", "", "x") },
    ]);
    expect(routes.map((r) => r.order_id)).toEqual(["1", "3"]);
    expect(routes[0]).toMatchObject({ from: "8450 Lawson Rd", to: "100 King St W" });
  });
  it("caps the list", () => {
    const many = Array.from({ length: 6 }, (_, i) => order(String(i), `A${i}`, `B${i}`));
    expect(bookAgainRoutes(many, 3)).toHaveLength(3);
  });
});

describe("small formatters", () => {
  it("shortAddress keeps the street line", () => {
    expect(shortAddress("100 King St W, Toronto, ON")).toBe("100 King St W");
    expect(shortAddress(null)).toBe("");
  });
  it("friendlyDate uses Toronto days", () => {
    const now = new Date("2026-10-15T16:00:00Z");
    expect(friendlyDate("2026-10-15T13:00:00Z", now)).toBe("Today");
    expect(friendlyDate("2026-10-14T13:00:00Z", now)).toBe("Yesterday");
    expect(friendlyDate("bad", now)).toBe("");
  });
  it("expiresIn counts down the held price", () => {
    const now = new Date("2026-10-15T16:00:00Z");
    expect(expiresIn("2026-10-15T16:14:00Z", now)).toBe("Price held for 14 min");
    expect(expiresIn("2026-10-15T15:00:00Z", now)).toBe("Quote expired");
  });
  it("detects offline errors", () => {
    expect(isOfflineError("Network request failed")).toBe(true);
    expect(isOfflineError("Aborted")).toBe(true);
    expect(isOfflineError("quote_expired")).toBe(false);
  });
});
