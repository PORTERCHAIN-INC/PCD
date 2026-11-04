import { describe, expect, it } from "vitest";
import {
  ADVICE_ACTIONS,
  adviceText,
  BLOCK_CHECKS,
  blockersFor,
  blockMessage,
  cardCopy,
  COPY_TABLES,
  handlingLabels,
} from "./index";

const spec = { flow_id: "pickup_batch", version: 1, steps: [] };
const NEW_BLOCKS = [
  "spot_check_incomplete",
  "per_parcel_scan_required",
  "count_not_entered",
  "photo_missing",
  "count_mismatch_unreported",
  "merchant_not_confirmed",
  "pickup_not_confirmed",
  "building_scan_incomplete",
  "handover_needs_photo_and_location",
  "handover_scan_mismatch",
  "leftover_without_disposition",
  "pickup_docs_missing",
  "instruction_not_acknowledged",
];
const NEW_CARDS = [
  "batch_parcel_list",
  "spot_check",
  "count_photo",
  "merchant_handover",
  "count_exception",
  "scan_parcel",
  "building_scan",
  "handover_out",
  "handover_in",
  "leftover_disposition",
  "pickup_docs",
  "instructions",
];

describe("bulk batch flows", () => {
  it("has EN/FR copy and a check for every new card/block", () => {
    for (const c of NEW_CARDS) {
      expect(COPY_TABLES.en[c]).toBeTruthy();
      expect(COPY_TABLES.fr[c]).toBeTruthy();
      expect(cardCopy(c, "fr").title).not.toEqual(cardCopy(c, "en").title === c ? "" : c);
    }
    for (const b of NEW_BLOCKS) {
      expect(BLOCK_CHECKS[b]).toBeTypeOf("function");
      expect(blockMessage(b, "fr")).not.toEqual(b);
    }
  });

  it("pickup gates: spot sample, per-parcel, count/photo, mismatch, handover", () => {
    const ids = [
      "spot_check_incomplete",
      "per_parcel_scan_required",
      "count_not_entered",
      "photo_missing",
      "count_mismatch_unreported",
      "merchant_not_confirmed",
    ];
    expect(
      blockersFor(ids, { spotSample: ["A"], scanRequired: ["RX"], expectedCount: 3 }, spec)
    ).toEqual([
      "spot_check_incomplete",
      "per_parcel_scan_required",
      "count_not_entered",
      "photo_missing",
      "merchant_not_confirmed",
    ]);
    expect(
      blockersFor(
        ids,
        {
          spotSample: ["A"],
          scanRequired: ["RX"],
          scanned: ["A", "RX"],
          counted: 2,
          expectedCount: 3,
          photo: true,
          merchantConfirmed: true,
        },
        spec
      )
    ).toEqual(["count_mismatch_unreported"]);
    expect(
      blockersFor(
        ids,
        {
          spotSample: ["A"],
          scanned: ["A"],
          counted: 2,
          expectedCount: 3,
          photo: true,
          merchantConfirmed: true,
          countException: true,
        },
        spec
      )
    ).toEqual([]);
  });

  it("delivery unlock, building scan, handover and leftovers", () => {
    expect(blockersFor(["pickup_not_confirmed"], {}, spec)).toEqual(["pickup_not_confirmed"]);
    expect(
      blockersFor(
        ["building_scan_incomplete"],
        { buildingExpected: ["A", "B"], scanned: ["A"] },
        spec
      )
    ).toHaveLength(1);
    expect(
      blockersFor(
        ["handover_needs_photo_and_location"],
        { photo: true, location: { lat: 1, lng: 2 } },
        spec
      )
    ).toEqual([]);
    expect(
      blockersFor(["handover_scan_mismatch"], { handoverExpected: ["A", "B"], counted: 2 }, spec)
    ).toEqual([]);
    expect(
      blockersFor(
        ["handover_scan_mismatch"],
        { handoverExpected: ["A", "B"], scanned: ["A"] },
        spec
      )
    ).toHaveLength(1);
    expect(
      blockersFor(
        ["leftover_without_disposition"],
        { leftovers: ["X"], dispositions: { X: "return" } },
        spec
      )
    ).toEqual([]);
  });

  it("documents and must-read instructions", () => {
    const c = {
      docsRequired: ["bol", "packing_list"],
      docsNonBlocking: ["packing_list"],
      docs: { bol: "captured" as const, packing_list: "missing" as const },
    };
    expect(blockersFor(["pickup_docs_missing"], c, spec)).toEqual([]);
    expect(
      blockersFor(["pickup_docs_missing"], { ...c, docs: { bol: "missing" as const } }, spec)
    ).toHaveLength(1);
    expect(
      blockersFor(["instruction_not_acknowledged"], { mustAck: ["i1"], acked: [] }, spec)
    ).toHaveLength(1);
    expect(
      blockersFor(["instruction_not_acknowledged"], { mustAck: ["i1"], acked: ["i1"] }, spec)
    ).toEqual([]);
  });

  it("scan advice text for every action, EN/FR", () => {
    for (const a of ADVICE_ACTIONS) {
      expect(adviceText({ action: a }, "en")).toBeTruthy();
      expect(adviceText({ action: a }, "fr")).not.toEqual(adviceText({ action: a }, "en"));
    }
    expect(adviceText({ action: "load", load_position: 1, stop_seq: 9, unit: "5" })).toBe(
      "Load position 1 — stop 9, unit 5"
    );
    expect(adviceText({ action: "hand_to_driver", to_driver_id: "B" })).toBe("Hand to driver B");
    expect(handlingLabels(["fragile", "dolly"], "fr")).toEqual(["Fragile", "Diable"]);
  });
});
