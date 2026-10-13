import { describe, expect, it } from "vitest";
import type { DispatchRoute, DispatchStop } from "../dispatchRoute";
import { daySummary, gpsMode, headsUpText, loadOrder, stopWarnings } from "./route";

const s = (o: Partial<DispatchStop>): DispatchStop => ({
  keys: [String(Math.random())],
  order_id: "o",
  order_number: "1",
  kind: "drop",
  status: "pending",
  address: "a",
  lat: 1,
  lng: 1,
  boxes: 1,
  needs_pod: false,
  notes: null,
  eta_s: 0,
  ...o,
});
const route = (stops: DispatchStop[]): DispatchRoute => ({
  id: "r",
  vehicle_class: "van",
  stops,
  next_index: 0,
  done: 0,
  total: stops.length,
});

describe("loadOrder", () => {
  it("loads the last delivery first and skips pickups and finished stops", () => {
    const r = route([
      s({ kind: "pickup", address: "P" }),
      s({ address: "A" }),
      s({ address: "B", status: "done" }),
      s({ address: "C" }),
    ]);
    expect(loadOrder(r).map((x) => [x.stop.address, x.position])).toEqual([
      ["C", 4],
      ["A", 2],
    ]);
  });
  it("is empty with no route", () => expect(loadOrder(null)).toEqual([]));
});

describe("daySummary", () => {
  it("counts done, failed, boxes and proofs", () => {
    const d = daySummary(
      route([
        s({ kind: "pickup", status: "done", boxes: 3 }),
        s({ status: "done", boxes: 2, needs_pod: true }),
        s({ status: "failed" }),
      ])
    );
    expect(d).toMatchObject({
      total: 3,
      done: 2,
      failed: 1,
      pickups: 1,
      drops: 1,
      boxes: 5,
      proofs: 1,
    });
  });
});

describe("headsUpText / gpsMode", () => {
  it("rounds ETA and never says 0 min", () => {
    expect(headsUpText(0.2, "drop")).toContain("about 1 min");
    expect(headsUpText(null, "pickup")).toContain("pick up");
  });
  it("saver below 20 % or in low-power mode", () => {
    expect(gpsMode(0.5, false)).toBe("high");
    expect(gpsMode(0.19, false)).toBe("saver");
    expect(gpsMode(0.9, true)).toBe("saver");
    expect(gpsMode(-1, false)).toBe("high");
  });
});

describe("stopWarnings", () => {
  const base = {
    stop: null,
    fixAgeMs: 1000,
    accuracyM: 10,
    battery: 0.8,
    offline: false,
    speedMps: 0,
  };
  it("is quiet when all is well", () => expect(stopWarnings(base)).toEqual([]));
  it("puts low battery first and caps at two", () => {
    const w = stopWarnings({ ...base, battery: 0.1, offline: true, stop: s({ liftgate: true }) });
    expect(w.map((x) => x.id)).toEqual(["battery", "offline"]);
  });
  it("flags lost GPS", () =>
    expect(stopWarnings({ ...base, fixAgeMs: 200_000 })[0]?.id).toBe("gps"));
});
