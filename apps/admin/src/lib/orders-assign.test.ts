import { describe, expect, it } from "vitest";
import { assignDriverLabel, canAssignDriver, isDeliveryLeg } from "./orders";
import { nextActionFor } from "@/components/orders/order360/shared";
import type { OrderDetail } from "./orders";

describe("assign driver after pickup", () => {
  it("picked-up orders can take a delivery driver", () => {
    for (const s of ["PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"]) {
      expect(isDeliveryLeg(s)).toBe(true);
      expect(canAssignDriver(s)).toBe(true);
    }
    expect(assignDriverLabel("PICKED_UP", true)).toBe("Reassign delivery driver");
    expect(assignDriverLabel("PICKED_UP", false)).toBe("Assign delivery driver");
  });

  it("pre-pickup states keep the normal labels", () => {
    expect(assignDriverLabel("DISPATCH_READY", false)).toBe("Assign driver");
    expect(assignDriverLabel("DRIVER_ACCEPTED", true)).toBe("Reassign driver");
    expect(isDeliveryLeg("AT_PICKUP")).toBe(false);
  });

  it("finished orders cannot be assigned", () => {
    for (const s of ["DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED", "CANCELLED", "FAILED"]) {
      expect(canAssignDriver(s)).toBe(false);
    }
  });

  it("next best action after pickup is assign delivery driver", () => {
    const next = nextActionFor({
      state: "PICKED_UP",
      driver_name: "Abdul",
    } as unknown as OrderDetail);
    expect(next.kind).toBe("assign");
    expect(next.label).toBe("Reassign delivery driver");
  });
});
