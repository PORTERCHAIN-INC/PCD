import { describe, expect, it } from "vitest";
import { getPrimaryAction } from "./jobs";

describe("delivery leg after pickup", () => {
  it("picked up → Start Delivery (out for delivery + receiver tracking)", () => {
    expect(
      getPrimaryAction("PICKED_UP", ["start_delivery", "arrive_delivery", "confirm_delivery"])
    ).toEqual({ key: "start_delivery", label: "Start Delivery" });
  });
  it("older API without start_delivery still offers Arrive", () => {
    expect(getPrimaryAction("PICKED_UP", ["arrive_delivery", "confirm_delivery"])?.key).toBe(
      "arrive_delivery"
    );
  });
  it("in transit → Arrive at Delivery; at destination → Confirm", () => {
    expect(getPrimaryAction("IN_TRANSIT", ["arrive_delivery", "confirm_delivery"])?.key).toBe(
      "arrive_delivery"
    );
    expect(getPrimaryAction("AT_DESTINATION", ["confirm_delivery"])?.key).toBe("confirm_delivery");
  });
});
