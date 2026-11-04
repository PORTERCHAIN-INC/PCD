import { describe, expect, it } from "vitest";
import {
  advance,
  blockMessage,
  cardCopy,
  COPY_TABLES,
  start,
  visibleSteps,
  type FlowSpec,
} from "./index";

const pharmacy: FlowSpec = {
  flow_id: "delivery_pharmacy_custody",
  version: 1,
  temp_range_c: [2, 8],
  steps: [
    { id: "arrive", card: "arrive_geofence", capture: [], block_if: ["not_at_stop"] },
    { id: "seal", card: "seal_check", capture: ["seal_no"], block_if: ["seal_mismatch"] },
    {
      id: "temp",
      card: "temp_read",
      capture: ["temp"],
      block_if: ["temp_out_of_range"],
      only_if: "cold_chain",
    },
    { id: "id", card: "id_check", capture: ["id_name_match"], block_if: ["id_fail"] },
    { id: "sign", card: "signature", capture: ["signature"], block_if: ["no_signature"] },
  ],
};

describe("driver-flows machine", () => {
  it("blocks on seal mismatch and temperature excursion", () => {
    let s = advance(start(pharmacy), { atStop: true }).state;
    expect(advance(s, { sealNo: "A1", expectedSealNo: "B2" }).blockedBy).toEqual(["seal_mismatch"]);
    s = advance(s, { sealNo: "B2", expectedSealNo: "B2" }).state;
    expect(advance(s, { tempC: 9 }).blockedBy).toEqual(["temp_out_of_range"]);
    s = advance(s, { tempC: 5 }).state;
    s = advance(s, { idNameMatch: true }).state;
    const last = advance(s, { signature: true });
    expect(last.state.done).toBe(true);
  });
  it("skips only_if steps when the flag is off", () => {
    expect(visibleSteps(pharmacy, { cold_chain: false }).map((x) => x.id)).not.toContain("temp");
  });
  it("fails closed on unknown checks", () => {
    const spec: FlowSpec = {
      flow_id: "x",
      version: 9,
      steps: [{ id: "a", card: "leave", capture: [], block_if: ["future_rule"] }],
    };
    expect(advance(start(spec), {}).blockedBy).toEqual(["future_rule"]);
  });
  it("has EN and FR copy for every card and block", () => {
    expect(Object.keys(COPY_TABLES.fr).sort()).toEqual(Object.keys(COPY_TABLES.en).sort());
    expect(Object.keys(COPY_TABLES.block_fr).sort()).toEqual(
      Object.keys(COPY_TABLES.block_en).sort()
    );
    expect(cardCopy("id_check", "fr").title).toMatch(/identité/);
    expect(blockMessage("under_19")).toMatch(/19/);
  });
});

import { flowView } from "./view";
describe("flowView", () => {
  it("marks the current card and shows its blockers in FR", () => {
    const v = flowView(pharmacy, { atStop: true, flags: { cold_chain: false } }, "fr", 1);
    expect(v.map((c) => c.state)).toEqual(["done", "current", "todo", "todo"]);
    expect(v[1].blockers[0]).toMatch(/Scellé/);
    expect(v[1].icon).toBe("shield-check");
  });
});
