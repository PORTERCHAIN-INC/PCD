import { describe, expect, it } from "vitest";
import { humanError } from "../errorCopy";

describe("chain-of-custody errors", () => {
  it("rejected package step reads as plain words", () => {
    expect(humanError("illegal_package_transition")).toMatch(/can't move to that step/);
  });
});
