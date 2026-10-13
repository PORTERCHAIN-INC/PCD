import { afterEach, describe, expect, it, vi } from "vitest";
import { clearStaffSession, LOGOUT_TIMEOUT_MS } from "./staff-session";

describe("clearStaffSession", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("clears the cookie and resolves even when the API logout hangs", async () => {
    vi.useFakeTimers();
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init: RequestInit) => {
        calls.push(`${init.method} ${url}`);
        if (init.method === "DELETE") return Promise.resolve(new Response("{}"));
        return new Promise((_, reject) =>
          init.signal?.addEventListener("abort", () => reject(new Error("aborted")))
        );
      })
    );
    const done = clearStaffSession("https://api.example.com");
    expect(calls).toContain("DELETE /api/auth/staff-session");
    await vi.advanceTimersByTimeAsync(LOGOUT_TIMEOUT_MS);
    await expect(done).resolves.toBeUndefined();
  });
});
