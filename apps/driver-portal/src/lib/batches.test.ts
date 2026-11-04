import { describe, expect, it, vi } from "vitest";
import {
  batchClient,
  buildingBlockers,
  leftovers,
  pickupBlockers,
  type BatchStop,
  type PickupView,
} from "./batches";

const step = (card: string, block_if: string[]) => ({ id: card, card, capture: [], block_if });
const view: PickupView = {
  route_id: "r1",
  status: "planned",
  expected: 3,
  scan_required: ["RX1"],
  spot_sample: ["A"],
  carry_for: {},
  pickup_source: "shop",
  parcels: [],
  documents: {
    items: [
      {
        doc_type: "bol",
        label: "Bill of lading",
        blocking: true,
        needs_seal: false,
        status: "todo",
      },
    ],
    blockers: ["bol"],
    reminders: [],
  },
  instructions: { items: [], must_ack: ["i1"] },
  flow_spec: {
    pickup: {
      flow_id: "pickup_batch",
      version: 1,
      steps: [
        step("instructions", ["instruction_not_acknowledged"]),
        step("spot_check", ["spot_check_incomplete"]),
        step("scan_packages", ["per_parcel_scan_required"]),
        step("count_photo", ["count_not_entered", "photo_missing"]),
        step("count_exception", ["count_mismatch_unreported"]),
        step("pickup_docs", ["pickup_docs_missing"]),
        step("merchant_handover", ["merchant_not_confirmed"]),
      ],
    },
    delivery: { flow_id: "d", version: 1, steps: [] },
    close: { flow_id: "c", version: 1, steps: [] },
    handover_give: { flow_id: "g", version: 1, steps: [] },
    handover_receive: { flow_id: "h", version: 1, steps: [] },
  },
};

describe("batch pickup gate", () => {
  it("lists every blocker until done", () => {
    expect(pickupBlockers(view, { scanned: [], acked: [] })).toEqual([
      "instruction_not_acknowledged",
      "spot_check_incomplete",
      "per_parcel_scan_required",
      "count_not_entered",
      "photo_missing",
      "pickup_docs_missing",
      "merchant_not_confirmed",
    ]);
    const done = {
      ...view,
      documents: {
        ...view.documents,
        items: [{ ...view.documents.items[0], status: "captured" as const }],
      },
    };
    expect(
      pickupBlockers(done, {
        scanned: ["A", "RX1"],
        counted: 2,
        photo: true,
        merchantConfirmed: true,
        acked: ["i1"],
      })
    ).toEqual(["count_mismatch_unreported"]);
    expect(
      pickupBlockers(done, {
        scanned: ["A", "RX1"],
        counted: 2,
        photo: true,
        merchantConfirmed: true,
        acked: ["i1"],
        countException: true,
      })
    ).toEqual([]);
  });

  it("building scan + leftovers", () => {
    const p = (barcode: string, status = "picked_up") => ({
      id: barcode,
      barcode,
      client_labels: [],
      stop_seq: 1,
      building_key: "B",
      unit: null,
      address: "",
      recipient: null,
      handling: [],
      scan_required: false,
      status,
    });
    const stop: BatchStop = {
      building_key: "B",
      address: "",
      stop_seq: 1,
      handling: [],
      parcels: [p("X"), p("Y"), p("Z", "delivered")],
      flow_spec: { flow_id: "d", version: 1, steps: [] },
    };
    expect(buildingBlockers(stop, ["X"])).toEqual(["building_scan_incomplete"]);
    expect(buildingBlockers(stop, ["X", "Y"])).toEqual([]);
    expect(leftovers([stop])).toEqual(["X", "Y"]);
  });

  it("client hits the driver API paths", async () => {
    const f = vi.fn().mockResolvedValue({});
    const c = batchClient(f as never);
    await c.captureDoc("r1", "bol", {
      scan_code: "S",
      shipper_name: "Sam",
      shipper_signature_key: "sig",
    });
    await c.ack("i1");
    await c.scan("r1", "#1001", "pickup", ["A"]);
    expect(f.mock.calls.map((x) => x[0])).toEqual([
      "/v1/doc-checklist/routes/r1/bol",
      "/v1/instructions/i1/ack",
      "/v1/batches/routes/r1/scan",
    ]);
    expect(JSON.parse(f.mock.calls[2][1].body)).toEqual({
      code: "#1001",
      phase: "pickup",
      scanned: ["A"],
    });
  });
});
