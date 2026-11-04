import { beforeEach, describe, expect, it, vi } from "vitest";

const calls: string[] = [];
const offline = vi.hoisted(() => ({
  flushOfflineQueues: vi.fn(),
  wipeOfflineData: vi.fn(),
}));
vi.mock("react-native", () => ({ Platform: { OS: "ios" } }));
vi.mock("../offline", () => offline);
vi.mock("../location", () => ({
  stopBackgroundLocation: vi.fn(async () => void calls.push("gps_off")),
}));
vi.mock("../consent", () => ({
  withdrawLocationConsent: vi.fn(async () => void calls.push("consent_off")),
}));
vi.mock("../push", () => ({
  unregisterRememberedPush: vi.fn(async () => void calls.push("push_off")),
}));

import { clearSession, getSessionSnapshot, setSessionSnapshot } from "../session";

beforeEach(() => {
  calls.length = 0;
  offline.flushOfflineQueues.mockReset().mockImplementation(async () => void calls.push("flush"));
  offline.wipeOfflineData.mockReset().mockImplementation(async () => void calls.push("wipe"));
});

describe("clearSession (sign-out wipe)", () => {
  it("syncs, stops GPS, unregisters push, signs out, then wipes local data", async () => {
    setSessionSnapshot({
      ready: true,
      signedIn: true,
      getToken: async () => "t",
      signOut: async () => void calls.push("auth_out"),
    });
    await clearSession();
    expect(calls).toEqual(["flush", "gps_off", "push_off", "auth_out", "wipe", "consent_off"]);
    expect(getSessionSnapshot().signedIn).toBe(false);
  });

  it("still wipes when offline sync and Keycloak sign-out both fail", async () => {
    offline.flushOfflineQueues.mockRejectedValue(new Error("offline"));
    setSessionSnapshot({
      ready: true,
      signedIn: true,
      getToken: async () => "t",
      signOut: async () => {
        throw new Error("auth_down");
      },
    });
    await expect(clearSession()).rejects.toThrow("auth_down");
    expect(offline.wipeOfflineData).toHaveBeenCalled();
    expect(getSessionSnapshot().signedIn).toBe(false);
  });
});
