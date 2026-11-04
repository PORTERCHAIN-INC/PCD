import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { flowFor } from "./flow-context";

const spec = (id: string) => ({ flow_id: id, version: 1, steps: [] });

describe("flow context (web = mobile)", () => {
  it("picks pickup before pickup, delivery after", () => {
    const fs = { documents: ["pod"], pickup: spec("pickup_x"), delivery: spec("delivery_y") };
    expect(flowFor({ flow_spec: fs, state: "ASSIGNED" }).spec?.flow_id).toBe("pickup_x");
    expect(flowFor({ flow_spec: fs, state: "PICKED_UP" }).spec?.flow_id).toBe("delivery_y");
    expect(flowFor({}).spec).toBeNull();
  });
  it("is the same mapping as the mobile app", () => {
    const strip = (s: string) => s.replace(/^\/\*\*.*\*\/$/m, "");
    const web = readFileSync(new URL("./flow-context.ts", import.meta.url), "utf8");
    const mob = readFileSync(
      new URL("../../../mobile-driver/src/flowContext.ts", import.meta.url),
      "utf8"
    );
    expect(strip(web)).toBe(strip(mob));
  });
});
