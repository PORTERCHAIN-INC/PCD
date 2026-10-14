import { describe, expect, it } from "vitest";
import {
  ago,
  buildIssues,
  filterCounts,
  filterIssues,
  glide,
  kpis,
  promiseTimeline,
} from "@/lib/today";
import type { DispatchExceptionItem, LiveEta } from "@/lib/dispatch";
import type { OpsStats, QueueOrder } from "@/lib/operations";

const ex = (o: Partial<DispatchExceptionItem>): DispatchExceptionItem => ({
  id: o.id ?? "x",
  kind: "late",
  type: "late",
  severity: "high",
  order_id: "o1",
  order_number: "PC-1",
  state: "in_transit",
  age_min: 5,
  status: "open",
  ...o,
});
const q = (o: Partial<QueueOrder>): QueueOrder =>
  ({
    id: "q1",
    order_number: "PC-9",
    tracking_number: "T",
    state: "pending",
    amount_cents: 0,
    merchant: null,
    driver: null,
    driver_id: null,
    pickup: "A",
    dropoff: "B",
    eta: null,
    sla: "",
    high_priority: false,
    created_at: null,
    ...o,
  }) as QueueOrder;

describe("buildIssues", () => {
  it("ranks critical first, then oldest", () => {
    const r = buildIssues(
      [
        ex({ id: "a", severity: "medium", age_min: 90 }),
        ex({ id: "b", severity: "critical", age_min: 1 }),
        ex({ id: "c", severity: "medium", age_min: 120 }),
      ],
      []
    );
    expect(r.map((i) => i.key)).toEqual(["b", "c", "a"]);
  });

  it("adds unassigned queue orders once and skips assigned ones", () => {
    const now = Date.parse("2026-10-14T15:00:00Z");
    const r = buildIssues(
      [ex({ id: "u", kind: "unassigned", type: "unassigned", order_id: "q1" })],
      [
        q({ id: "q1" }),
        q({ id: "q2", created_at: "2026-10-14T14:30:00Z" }),
        q({ id: "q3", driver_id: "d1" }),
      ],
      now
    );
    expect(r.map((i) => i.order_id).sort()).toEqual(["q1", "q2"]);
    const q2 = r.find((i) => i.order_id === "q2")!;
    expect(q2.severity).toBe("high");
    expect(q2.age_min).toBe(30);
    expect(q2.action).toBe("offer");
  });

  it("keeps one row per order (a late order is not repeated as unassigned)", () => {
    const r = buildIssues([ex({ id: "l", kind: "late", order_id: "q1" })], [q({ id: "q1" })]);
    expect(r).toHaveLength(1);
    expect(r[0].kind).toBe("late");
  });

  it("prefers a suggested fix over a bare offer", () => {
    const [i] = buildIssues(
      [
        ex({
          kind: "unassigned",
          fixes: [{ action: "reassign", label: "Give to Sam", why: "closest", params: {} }],
        }),
      ],
      []
    );
    expect(i.action).toBe("fix");
    expect(i.detail).toBe("closest");
  });
});

describe("filters + kpis", () => {
  const issues = buildIssues(
    [
      ex({ id: "1", kind: "late" }),
      ex({ id: "2", kind: "failed" }),
      ex({ id: "3", kind: "exception", type: "DRIVER_TIMEOUT" }),
    ],
    [q({ id: "q9" })]
  );
  it("buckets late / unassigned / failed", () => {
    expect(filterCounts(issues)).toEqual({ all: 4, late: 1, unassigned: 2, failed: 1 });
    expect(filterIssues(issues, "failed").map((i) => i.key)).toEqual(["2"]);
  });
  it("computes the 4 numbers", () => {
    const etas = [
      { status: "on_time" },
      { status: "late" },
      { status: "on_time" },
      { status: "unknown" },
    ] as LiveEta[];
    const stats = { orders_today: 40, completed_today: 12, waiting_dispatch: 1 } as OpsStats;
    expect(kpis(stats, etas, issues)).toEqual({
      onTimePct: 67,
      unassigned: 2,
      atRisk: 1,
      done: 12,
      total: 40,
    });
    expect(kpis(null, [], []).onTimePct).toBeNull();
  });
});

describe("promiseTimeline", () => {
  it("marks steps from events and current state", () => {
    const t = promiseTimeline("in_transit", [
      { status: "created", at: "2026-10-14T13:00:00Z" },
      { event_type: "order.assigned", occurred_at: "2026-10-14T13:05:00Z" },
    ]);
    expect(t.map((s) => s.done)).toEqual([true, true, true, false]);
    expect(t[1].at).toBe("2026-10-14T13:05:00Z");
  });
});

describe("ago", () => {
  it("formats freshness", () => {
    expect(ago(null)).toBe("—");
    expect(ago(1000, 3000)).toBe("live");
    expect(ago(0 + 1, 125_001)).toBe("2m ago");
  });
});

describe("glide", () => {
  const a = [{ id: "d1", lat: 43.65, lng: -79.38 }];
  it("eases between polls and lands exactly", () => {
    const to = [{ id: "d1", lat: 43.66, lng: -79.37, name: "J" }];
    expect(glide(a, to, 0)[0].lat).toBeCloseTo(43.65);
    const mid = glide(a, to, 0.5)[0];
    expect(mid.lat).toBeGreaterThan(43.655); // ease-out is past halfway at t=.5
    expect(mid.name).toBe("J");
    expect(glide(a, to, 1)[0]).toEqual(to[0]);
  });
  it("snaps big jumps and new drivers", () => {
    const to = [
      { id: "d1", lat: 43.9, lng: -79.38 },
      { id: "d2", lat: 43.7, lng: -79.4 },
    ];
    expect(glide(a, to, 0.1)).toEqual(to);
  });
});

describe("optimizeToast", () => {
  it("summarises the auto-committed plan", async () => {
    const { optimizeToast } = await import("@/lib/dispatch");
    const route = (driver_id: string | null) => ({ driver_id }) as never;
    expect(
      optimizeToast({
        routes: [route("d1"), route("d2"), route(null)],
        summary: {
          commit: { assigned: 5, skipped: [{ order_id: "x", reason: "already picked_up" }] },
        },
      })
    ).toBe("5 orders assigned on 2 routes · 1 kept as-is");
    expect(optimizeToast({ routes: [], summary: { commit: { assigned: 0, skipped: [] } } })).toBe(
      "Already optimal · nothing to assign"
    );
  });
});

describe("live updates", () => {
  it("moves only drivers already on the board, newest fix wins", async () => {
    const { applyDriverFix } = await import("@/lib/today");
    const snap = {
      drivers: [{ id: "d1", lat: 1, lng: 1, recorded_at: "2026-10-14T16:00:10Z", name: "J" }],
      orders: [],
    };
    const moved = applyDriverFix(snap, {
      type: "driver",
      id: "d1",
      lat: 2,
      lng: 3,
      at: "2026-10-14T16:00:20Z",
    })!;
    expect(moved.drivers[0]).toMatchObject({ lat: 2, lng: 3, name: "J" });
    expect(snap.drivers[0].lat).toBe(1); // immutable
    expect(
      applyDriverFix(snap, { type: "driver", id: "dX", lat: 9, lng: 9, at: "2026-10-14T16:00:20Z" })
    ).toBe(snap);
    expect(
      applyDriverFix(snap, { type: "driver", id: "d1", lat: 9, lng: 9, at: "2026-10-14T16:00:00Z" })
    ).toBe(snap);
  });
  it("maps events to stale queries", async () => {
    const { staleKeysFor } = await import("@/lib/today");
    expect(staleKeysFor({ type: "order", id: "o", event: "order.delivered" })).toContain(
      "today-map"
    );
    expect(staleKeysFor({ type: "exception", id: "e", event: "exception.opened" })).toContain(
      "today-exceptions"
    );
    expect(staleKeysFor({ type: "driver", id: "d", lat: 0, lng: 0 })).toEqual([]);
  });
});
