import { afterEach, describe, expect, it, vi } from "vitest";
import { isApiError, isNetworkError } from "../netErrors";

vi.mock("react-native", () => ({ Platform: { OS: "ios" } }));
vi.mock("../session", () => ({ requireBearer: async () => "tok" }));

import { deliverStop } from "../api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("driverFetch error classification", () => {
  it("no HTTP response → NetworkError (queueable)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Network request failed")));
    const err = await deliverStop("r1", "s1").catch((e: unknown) => e);
    expect(isNetworkError(err)).toBe(true);
    expect(isApiError(err)).toBe(false);
  });

  it("timeout (abort) → NetworkError", async () => {
    const abort = Object.assign(new Error("aborted"), { name: "AbortError" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    const err = await deliverStop("r1", "s1").catch((e: unknown) => e);
    expect(isNetworkError(err)).toBe(true);
    expect((err as Error).message).toBe("network_timeout");
  });

  it("server rejection → ApiError with the server's message and status (not queueable)", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ detail: { code: "pod_required", message: "Capture a photo first" } }),
            { status: 422 }
          )
        )
    );
    const err = await deliverStop("r1", "s1").catch((e: unknown) => e);
    expect(isApiError(err)).toBe(true);
    expect(isNetworkError(err)).toBe(false);
    expect(err).toMatchObject({ status: 422, message: "Capture a photo first" });
  });
});
