import { afterEach, describe, expect, it, vi } from "vitest";
import { isApiError, isNetworkError } from "../netErrors";

vi.mock("react-native", () => ({ Platform: { OS: "ios" } }));
const bearer = vi.fn(async (fresh?: boolean) => (fresh ? "fresh-tok" : "stale-tok"));
vi.mock("../session", () => ({ requireBearer: (fresh?: boolean) => bearer(fresh) }));

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

  it("401 with a stale token → one retry with a fresh token, then succeeds", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "token_expired" }), { status: 401 })
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(deliverStop("r1", "s1")).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const auth = (i: number) =>
      (fetchMock.mock.calls[i][1] as RequestInit).headers as Record<string, string>;
    expect(auth(0).Authorization).toBe("Bearer stale-tok");
    expect(auth(1).Authorization).toBe("Bearer fresh-tok");
  });

  it("401 twice → ApiError 401 (no retry loop)", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response("{}", { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);
    const err = await deliverStop("r1", "s1").catch((e: unknown) => e);
    expect(err).toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
