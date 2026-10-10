import { describe, expect, it } from "vitest";
import { applyLocal, type DriverDispatchRoute, type RouteStop } from "@/lib/dispatch-route";
import {
  enqueue,
  flush,
  isOfflineError,
  type QueueStore,
  type QueuedAction,
} from "@/lib/offline-queue";

function memStore(): QueueStore {
  let state = {
    queue: [] as QueuedAction[],
    rejected: [] as { action: QueuedAction; reason: string }[],
  };
  return {
    read: () => structuredClone(state),
    write: (s) => {
      state = structuredClone(s);
    },
  };
}

const act = (id: string): QueuedAction => ({ id, kind: "checkin", body: { client_id: id }, at: 0 });

describe("offline queue", () => {
  it("keeps order, dedupes by client id and stops at the first offline failure", async () => {
    const store = memStore();
    enqueue(store, act("a"));
    enqueue(store, act("a"));
    enqueue(store, act("b"));
    enqueue(store, act("c"));
    const sent: string[] = [];
    const out = await flush(store, async (a) => {
      if (a.id === "b" && sent.length === 1 && !sent.includes("retry")) {
        sent.push("retry");
        throw new TypeError("Failed to fetch");
      }
      sent.push(a.id);
    });
    expect(out).toEqual({ sent: 1, left: 2, rejected: 0 });
    const again = await flush(store, async (a) => {
      sent.push(a.id);
    });
    expect(again.left).toBe(0);
    expect(sent.filter((s) => s !== "retry")).toEqual(["a", "b", "c"]);
  });

  it("moves a server rejection aside and carries on", async () => {
    const store = memStore();
    enqueue(store, act("x"));
    enqueue(store, act("y"));
    const out = await flush(store, async (a) => {
      if (a.id === "x") throw new Error("scan_required:pickup:ABC-1");
    });
    expect(out).toEqual({ sent: 1, left: 0, rejected: 1 });
    expect(store.read().rejected[0].reason).toContain("scan_required");
  });

  it("tells no-signal from a refusal", () => {
    expect(isOfflineError(new TypeError("Failed to fetch"), true)).toBe(true);
    expect(isOfflineError(new Error("pod_required"), true)).toBe(false);
    expect(isOfflineError(new Error("anything"), false)).toBe(true);
  });
});

const stop = (k: string, status: RouteStop["status"] = "pending"): RouteStop => ({
  keys: [k],
  order_id: "o",
  order_number: null,
  kind: "drop",
  status,
  address: null,
  lat: null,
  lng: null,
  fsa: null,
  boxes: 1,
  needs_pod: true,
  notes: null,
  eta_s: 0,
  scan: null,
});

describe("local route while offline", () => {
  it("advances to the next stop", () => {
    const route: DriverDispatchRoute = {
      id: "r",
      vehicle_class: "van",
      stops: [stop("a", "arrived"), stop("b")],
      next_index: 0,
      done: 0,
      total: 2,
    };
    const after = applyLocal(route, ["a"], "delivered");
    expect(after.next_index).toBe(1);
    expect(after.done).toBe(1);
    expect(applyLocal(after, ["b"], "arrived").stops[1].status).toBe("arrived");
  });
});
