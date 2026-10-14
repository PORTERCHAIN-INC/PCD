import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../netErrors";
import { asyncStorageMock, resetNative, secureBlobMock } from "./nativeMocks";

vi.mock("@react-native-async-storage/async-storage", () => ({ default: asyncStorageMock }));
vi.mock("expo-crypto", async () => {
  const nodeCrypto = await import("node:crypto");
  return { randomUUID: () => nodeCrypto.randomUUID() };
});
vi.mock("../secureBlob", () => secureBlobMock);

const api = vi.hoisted(() => ({
  queueOffline: vi.fn(),
  syncOffline: vi.fn(),
  fetchOfflineStatus: vi.fn(),
  retryServerAction: vi.fn(),
  discardServerAction: vi.fn(),
}));
vi.mock("../api", () => api);

import { enqueueOfflineAction, flushOfflineQueues, readQueue, readRejected } from "../offline";
import { discardRefused, loadRefused, retryRefused, whereLabel } from "../refusedReview";

const serverRow = {
  id: "srv-1",
  action_type: "stop_complete",
  payload: { stop_id: "stop-abcdef123", order_id: "ord-12345678xyz" },
  status: "failed",
  error: "stop_already_closed",
  created_at: "2026-10-14T18:00:00+00:00",
};

async function parkOne() {
  await enqueueOfflineAction("stop_arrive", { stop_id: "s-local-1" });
  api.queueOffline.mockRejectedValueOnce(new ApiError("not_at_stop", 422));
  await flushOfflineQueues();
  expect(await readRejected()).toHaveLength(1);
}

beforeEach(() => {
  resetNative();
  api.queueOffline.mockReset().mockResolvedValue({});
  api.syncOffline.mockReset().mockResolvedValue({ conflicts_resolved: 0, failed: 0 });
  api.fetchOfflineStatus
    .mockReset()
    .mockResolvedValue({ pending_count: 0, failed_count: 1, failed: [serverRow] });
  api.retryServerAction.mockReset();
  api.discardServerAction.mockReset().mockResolvedValue({ ...serverRow, status: "discarded" });
});

describe("refused review", () => {
  it("lists device-parked and server-failed items with action, place, time and reason", async () => {
    await parkOne();
    const items = await loadRefused();
    expect(items.map((i) => i.source).sort()).toEqual(["device", "server"]);
    const srv = items.find((i) => i.source === "server")!;
    expect(srv.action).toBe("Completed stop");
    expect(srv.where).toBe("Job ord-1234 · Stop stop-abc");
    expect(srv.at).toBe(serverRow.created_at);
  });

  it("still lists device items when the server is unreachable", async () => {
    await parkOne();
    api.fetchOfflineStatus.mockRejectedValue(new Error("offline"));
    expect((await loadRefused()).map((i) => i.source)).toEqual(["device"]);
  });

  it("retry of a device item re-queues and sends it", async () => {
    await parkOne();
    const [dev] = (await loadRefused()).filter((i) => i.source === "device");
    expect(await retryRefused(dev)).toBeNull();
    expect(await readRejected()).toHaveLength(0);
    expect(await readQueue()).toHaveLength(0);
  });

  it("retry of a device item refused again stays parked and says so", async () => {
    await parkOne();
    const [dev] = (await loadRefused()).filter((i) => i.source === "device");
    api.queueOffline.mockRejectedValueOnce(new ApiError("not_at_stop", 422));
    expect(await retryRefused(dev)).toMatch(/Refused again/);
    expect(await readRejected()).toHaveLength(1);
  });

  it("discard removes a device item; server items go through the driver endpoints", async () => {
    await parkOne();
    const items = await loadRefused();
    await discardRefused(items.find((i) => i.source === "device")!);
    expect(await readRejected()).toHaveLength(0);
    await discardRefused(items.find((i) => i.source === "server")!);
    expect(api.discardServerAction).toHaveBeenCalledWith("srv-1");
    api.retryServerAction.mockResolvedValue({ ...serverRow, error: "stop_already_closed" });
    expect(await retryRefused(items.find((i) => i.source === "server")!)).toBeTruthy();
  });

  it("whereLabel tolerates missing ids", () => {
    expect(whereLabel({})).toBeNull();
    expect(whereLabel(null)).toBeNull();
  });
});
