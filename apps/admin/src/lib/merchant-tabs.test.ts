import { describe, expect, it } from "vitest";
import { parseMerchantTab } from "./merchant-tabs";

describe("parseMerchantTab", () => {
  it("defaults to overview", () => {
    expect(parseMerchantTab(null).tab).toBe("overview");
  });
  it("maps old tab ids into the five tabs", () => {
    expect(parseMerchantTab("pricing")).toMatchObject({ tab: "money", money: "pricing" });
    expect(parseMerchantTab("api").tab).toBe("connections");
    expect(parseMerchantTab("settings")).toMatchObject({ tab: "people", people: "settings" });
    expect(parseMerchantTab("invoices")).toMatchObject({ tab: "money", money: "invoices" });
    expect(parseMerchantTab("tasks")).toMatchObject({
      tab: "people",
      people: "activity",
      activity: "tasks",
    });
  });
  it("reads tab + panel", () => {
    expect(parseMerchantTab("money", "credit")).toMatchObject({ tab: "money", money: "credit" });
    expect(parseMerchantTab("people", "documents")).toMatchObject({
      tab: "people",
      people: "documents",
    });
    expect(parseMerchantTab("people", "timeline")).toMatchObject({
      people: "activity",
      activity: "timeline",
    });
  });
});
