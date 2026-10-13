import { describe, expect, it } from "vitest";
import { layoutFor } from "./layout";

describe("layoutFor", () => {
  it("iPhone SE is compact", () =>
    expect(layoutFor(375, 667)).toMatchObject({ compact: true, landscape: false }));
  it("Pro Max is roomy", () =>
    expect(layoutFor(430, 932)).toMatchObject({ roomy: true, compact: false }));
  it("dashboard mount is landscape with a wide cap", () =>
    expect(layoutFor(852, 393)).toMatchObject({ landscape: true, maxContent: 1100 }));
  it("big Android is not compact", () => expect(layoutFor(412, 915).compact).toBe(false));
});
