import { describe, expect, it } from "vitest";
import { canAssignPartner, COURIER_KINDS, openCourierLeg } from "./partner-assign";

describe("L97 assign to fleet partner", () => {
  it("allows open, driverless orders with no live partner leg", () => {
    expect(canAssignPartner("DISPATCH_READY", false, [])).toBe(true);
    expect(canAssignPartner("BOOKED", false, [{ status: "cancelled" }])).toBe(true);
    expect(canAssignPartner("DRIVER_REJECTED", false, [{ status: "delivered" }])).toBe(true);
  });
  it("blocks when a driver has it, the order moved on, or a partner leg is live", () => {
    expect(canAssignPartner("DISPATCH_READY", true, [])).toBe(false);
    expect(canAssignPartner("PICKED_UP", false, [])).toBe(false);
    expect(canAssignPartner(null, false, [])).toBe(false);
    expect(canAssignPartner("DISPATCH_READY", false, [{ status: "requested" }])).toBe(false);
  });
  it("finds the live leg and only offers courier kinds", () => {
    expect(openCourierLeg([{ status: "cancelled" }, { status: "accepted" }])?.status).toBe(
      "accepted"
    );
    expect(COURIER_KINDS.has("courier") && COURIER_KINDS.has("3pl")).toBe(true);
    expect(COURIER_KINDS.has("warehouse")).toBe(false);
  });
});
