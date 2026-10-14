import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError } from "../netErrors";

const calls: string[] = [];
const api = vi.hoisted(() => ({
  podPhoto: vi.fn(),
  podSignature: vi.fn(),
  podIdCheck: vi.fn(),
  podComplete: vi.fn(),
  deliverStop: vi.fn(),
}));
const queued: string[] = [];
vi.mock("../api", () => api);
vi.mock("../offline", () => ({
  // Same contract as the real runOnlineOrQueue: queue only on NetworkError.
  runOnlineOrQueue: async (type: string, _p: unknown, online: () => Promise<unknown>) => {
    if (queued.length) {
      queued.push(type);
      return "queued";
    }
    try {
      await online();
      calls.push(type);
      return "online";
    } catch (err) {
      if (err instanceof NetworkError) {
        queued.push(type);
        return "queued";
      }
      throw err;
    }
  },
}));

import { completeStop } from "../stop/completeStop";
import { emptyPodDraft } from "../stop/podDraft";

const args = {
  routeId: "r1",
  stopId: "s1",
  otpRequired: false,
  podRequirements: { enforced: true, photo_or_signature: true },
};

beforeEach(() => {
  calls.length = 0;
  queued.length = 0;
  Object.values(api).forEach((fn) => fn.mockReset().mockResolvedValue({}));
});

describe("completeStop", () => {
  it("pickup: only deliver_stop", async () => {
    expect(await completeStop({ ...args, kind: "pickup", pod: emptyPodDraft() })).toBe("online");
    expect(calls).toEqual(["deliver_stop"]);
  });

  it("delivery: proof → pod_complete → deliver_stop, in order", async () => {
    const pod = { ...emptyPodDraft(), photoUrl: "data:p", signature: "data:s" };
    await completeStop({ ...args, kind: "delivery", pod });
    expect(calls).toEqual(["camera_upload", "pod_signature", "pod_complete", "deliver_stop"]);
  });

  it("refuses locally when the server's POD policy is not met (nothing sent)", async () => {
    await expect(completeStop({ ...args, kind: "delivery", pod: emptyPodDraft() })).rejects.toThrow(
      /photo or the receiver's signature/
    );
    expect(calls).toEqual([]);
  });

  it("server rejection surfaces to the driver; never reported as delivered", async () => {
    api.podComplete.mockRejectedValue(new ApiError("otp_invalid", 422));
    const pod = { ...emptyPodDraft(), signature: "s" };
    await expect(completeStop({ ...args, kind: "delivery", pod })).rejects.toThrow("otp_invalid");
    expect(api.deliverStop).not.toHaveBeenCalled();
  });

  it("no signal mid-way: the rest queues behind it and the stop is 'queued'", async () => {
    api.podSignature.mockRejectedValue(new NetworkError());
    const pod = { ...emptyPodDraft(), photoUrl: "p", signature: "s" };
    expect(await completeStop({ ...args, kind: "delivery", pod })).toBe("queued");
    expect(calls).toEqual(["camera_upload"]);
    expect(queued).toEqual(["pod_signature", "pod_complete", "deliver_stop"]);
  });

  it("no stop → error, nothing sent", async () => {
    await expect(
      completeStop({ ...args, stopId: null, kind: "pickup", pod: emptyPodDraft() })
    ).rejects.toThrow("no_stop");
  });
});
