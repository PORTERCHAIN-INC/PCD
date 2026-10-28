import { describe, expect, it } from "vitest";
import { actionErrorMessage } from "./jobs";

describe("chain-of-custody scan messages", () => {
  it("explains a rejected package step", () => {
    expect(actionErrorMessage("illegal_package_transition")).toMatch(/can't move to that step/);
  });
  it("mentions registered partner barcodes for unknown labels", () => {
    expect(actionErrorMessage("invalid_label_qr")).toMatch(/registered for this order/);
  });
});
