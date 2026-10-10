import { describe, expect, it } from "vitest";
import { dropBoxes } from "@/lib/dispatch-route";

describe("dropBoxes", () => {
  const scan = { scanned: 1, missing_suffixes: ["A-1", "A-2"] };
  it("leaves open boxes unscanned until the driver delivers short", () => {
    const boxes = dropBoxes(scan, ["A-1"], false);
    expect(boxes.map((b) => [b.done, b.missing])).toEqual([
      [true, false],
      [true, false],
      [false, false],
    ]);
  });
  it("marks every unscanned box missing when delivering short", () => {
    const boxes = dropBoxes(scan, ["A-1"], true);
    expect(boxes.find((b) => b.code === "A-2")).toMatchObject({ done: false, missing: true });
    expect(boxes.find((b) => b.code === "A-1")).toMatchObject({ done: true, missing: false });
  });
});
