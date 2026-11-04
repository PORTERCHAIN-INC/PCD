import { describe, expect, it } from "vitest";
import { capabilityDiff, typeLabel } from "./orgs";

describe("orgs helpers", () => {
  it("diffs capabilities against type defaults", () => {
    expect(
      capabilityDiff({ shopify_app: true, pallets: true, cod: false }, ["shopify_app", "cod"])
    ).toEqual({
      added: ["pallets"],
      removed: ["cod"],
    });
  });
  it("labels types with a readable fallback", () => {
    expect(
      typeLabel(
        [{ code: "small_shop", label: "Small shop", roles: [], documents: [] }],
        "small_shop"
      )
    ).toBe("Small shop");
    expect(typeLabel(undefined, "shopify_merchant")).toBe("shopify merchant");
  });
});
