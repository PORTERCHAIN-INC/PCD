import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError } from "../netErrors";
import { asyncStorageMock, blobs, resetNative, secureBlobMock, storage } from "./nativeMocks";

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
}));
vi.mock("../api", () => api);

import {
  enqueueOfflineAction,
  flushOfflineQueues,
  newClientId,
  queuedStopIds,
  readQueue,
  readRejected,
  runOnlineOrQueue,
  wipeOfflineData,
} from "../offline";

beforeEach(() => {
  resetNative();
  api.queueOffline.mockReset().mockResolvedValue({});
  api.syncOffline.mockReset().mockResolvedValue({ conflicts_resolved: 0, failed: 0 });
  api.fetchOfflineStatus.mockReset().mockResolvedValue({ pending_count: 0, failed_count: 0 });
});

describe("runOnlineOrQueue", () => {
  it("runs online and queues nothing when the server accepts", async () => {
    const online = vi.fn().mockResolvedValue({});
    await expect(runOnlineOrQueue("deliver_stop", { stop_id: "s1" }, online)).resolves.toBe(
      "online"
    );
    expect(await readQueue()).toHaveLength(0);
  });

  it("queues only when there is no connection", async () => {
    const online = vi.fn().mockRejectedValue(new NetworkError());
    await expect(runOnlineOrQueue("deliver_stop", { stop_id: "s1" }, online)).resolves.toBe(
      "queued"
    );
    expect(await queuedStopIds()).toEqual(["s1"]);
  });

  it("rethrows a server rejection and never queues it as done", async () => {
    const online = vi.fn().mockRejectedValue(new ApiError("pod_required", 422));
    await expect(runOnlineOrQueue("deliver_stop", { stop_id: "s1" }, online)).rejects.toThrow(
      "pod_required"
    );
    expect(await readQueue()).toHaveLength(0);
    expect(await queuedStopIds()).toEqual([]);
  });

  it("rethrows unknown errors (bugs) instead of queueing", async () => {
    const online = vi.fn().mockRejectedValue(new TypeError("boom"));
    await expect(runOnlineOrQueue("arrive_stop", {}, online)).rejects.toThrow("boom");
    expect(await readQueue()).toHaveLength(0);
  });

  it("queues behind older queued actions to keep server order", async () => {
    await enqueueOfflineAction("camera_upload", { stop_id: "s1", file_url: "data:x" });
    const online = vi.fn();
    await expect(runOnlineOrQueue("deliver_stop", { stop_id: "s1" }, online)).resolves.toBe(
      "queued"
    );
    expect(online).not.toHaveBeenCalled();
    expect((await readQueue()).map((q) => q.action_type)).toEqual([
      "camera_upload",
      "deliver_stop",
    ]);
  });
});

describe("offline queue storage", () => {
  it("keeps photos/signatures/OTP out of AsyncStorage (encrypted blob instead)", async () => {
    await enqueueOfflineAction("pod_signature", {
      stop_id: "s1",
      signature_data: "SIG-SECRET",
      otp: "1234",
    });
    const raw = [...storage.values()].join("");
    expect(raw).not.toContain("SIG-SECRET");
    expect(raw).not.toContain("1234");
    const [item] = await readQueue();
    expect(item.blob_id).toBeTruthy();
    expect(blobs.get(item.blob_id as string)).toEqual({
      signature_data: "SIG-SECRET",
      otp: "1234",
    });
  });

  it("surfaces a full/broken store instead of losing the action, and cleans up the blob", async () => {
    asyncStorageMock.setItem.mockRejectedValueOnce(new Error("quota"));
    await expect(
      enqueueOfflineAction("camera_upload", { stop_id: "s1", file_url: "data:img" })
    ).rejects.toThrow("offline_queue_full");
    expect(blobs.size).toBe(0);
  });

  it("issues RFC 4122 UUID idempotency keys with no collisions", () => {
    const ids = new Set(Array.from({ length: 5000 }, () => newClientId()));
    expect(ids.size).toBe(5000);
    for (const id of [...ids].slice(0, 5)) expect(id).toMatch(/^[0-9a-f-]{36}$/);
  });
});

describe("flushOfflineQueues", () => {
  it("replays in order with the decrypted proof and the same client_id, then deletes the blob", async () => {
    const a = await enqueueOfflineAction("camera_upload", { stop_id: "s1", file_url: "data:img" });
    const b = await enqueueOfflineAction("deliver_stop", { stop_id: "s1" });
    const res = await flushOfflineQueues();
    expect(api.queueOffline.mock.calls).toEqual([
      ["camera_upload", { stop_id: "s1", file_url: "data:img" }, a.client_id],
      ["deliver_stop", { stop_id: "s1" }, b.client_id],
    ]);
    expect(res).toMatchObject({ queued: 2, synced: true, rejected: 0 });
    expect(await readQueue()).toHaveLength(0);
    expect(blobs.size).toBe(0);
  });

  it("stops at the first network failure and keeps the rest (no loss)", async () => {
    await enqueueOfflineAction("arrive_stop", { stop_id: "s1" });
    await enqueueOfflineAction("deliver_stop", { stop_id: "s1" });
    api.queueOffline.mockResolvedValueOnce({}).mockRejectedValueOnce(new NetworkError());
    const res = await flushOfflineQueues();
    expect(res.queued).toBe(1);
    expect((await readQueue()).map((q) => q.action_type)).toEqual(["deliver_stop"]);
  });

  it("keeps everything on a 5xx so it retries later", async () => {
    await enqueueOfflineAction("deliver_stop", { stop_id: "s1" });
    api.queueOffline.mockRejectedValueOnce(new ApiError("http_503", 503));
    await flushOfflineQueues();
    expect(await readQueue()).toHaveLength(1);
  });

  it("parks a 4xx-refused action where the driver can see it, and carries on", async () => {
    await enqueueOfflineAction("deliver_stop", { stop_id: "s1" });
    await enqueueOfflineAction("deliver_stop", { stop_id: "s2" });
    api.queueOffline.mockRejectedValueOnce(new ApiError("stop_closed", 409));
    const res = await flushOfflineQueues();
    expect(res.rejected).toBe(1);
    expect(await readQueue()).toHaveLength(0);
    const parked = await readRejected();
    expect(parked).toHaveLength(1);
    expect(parked[0]).toMatchObject({ rejected_reason: "stop_closed", payload: { stop_id: "s1" } });
  });

  it("never sends half a proof when the encrypted file is unreadable", async () => {
    const item = await enqueueOfflineAction("camera_upload", {
      stop_id: "s1",
      file_url: "data:img",
    });
    blobs.delete(item.blob_id as string);
    const res = await flushOfflineQueues();
    expect(api.queueOffline).not.toHaveBeenCalledWith(
      "camera_upload",
      expect.anything(),
      expect.anything()
    );
    expect(res.rejected).toBe(1);
  });
});

describe("wipeOfflineData (sign-out)", () => {
  it("removes queue, refused actions, GPS and every encrypted file", async () => {
    await enqueueOfflineAction("camera_upload", { stop_id: "s1", file_url: "data:img" });
    storage.set("porterchain_driver_gps_buffer", JSON.stringify([{ lat: 43.6, lng: -79.4 }]));
    storage.set("porterchain_driver_offline_rejected", "[]");
    await wipeOfflineData();
    expect(storage.size).toBe(0);
    expect(blobs.size).toBe(0);
    expect(secureBlobMock.wipeSecureBlobs).toHaveBeenCalled();
  });
});
