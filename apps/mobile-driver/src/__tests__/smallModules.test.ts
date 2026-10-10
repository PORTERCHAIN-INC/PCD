import { beforeEach, describe, expect, it, vi } from "vitest";
import { asyncStorageMock, storage } from "./nativeMocks";

vi.mock("@react-native-async-storage/async-storage", () => ({ default: asyncStorageMock }));
vi.mock("../handshake", () => ({
  isOnboardingBlocked: (m: string | null) => Boolean(m?.startsWith("driver_onboarding_blocked:")),
}));

import {
  CONSENT_VERSION,
  readLocationConsent,
  saveLocationConsent,
  withdrawLocationConsent,
} from "../consent";
import { humanError, isSilentError, needsAccountSwitch } from "../errorCopy";
import { mergeOfflineHandshake } from "../fieldState";
import { canEnterRoute } from "../gate";
import type { Handshake } from "../types";

const hs = (over: Partial<Handshake>): Handshake =>
  ({ api: "up", auth: "up", error: null, ...over }) as Handshake;

beforeEach(() => storage.clear());

describe("location consent", () => {
  it("absent until agreed; versioned; withdrawable", async () => {
    expect(await readLocationConsent()).toBeNull();
    const saved = await saveLocationConsent(new Date("2026-10-09T12:00:00Z"));
    expect(saved).toEqual({ version: CONSENT_VERSION, agreedAt: "2026-10-09T12:00:00.000Z" });
    expect(await readLocationConsent()).toEqual(saved);
    await withdrawLocationConsent();
    expect(await readLocationConsent()).toBeNull();
  });

  it("an older consent version must be asked again", async () => {
    storage.set(
      "porterchain_driver_location_consent",
      JSON.stringify({ version: 0, agreedAt: "x" })
    );
    expect(await readLocationConsent()).toBeNull();
  });
});

describe("humanError", () => {
  it("never shows raw codes or stack text", () => {
    expect(humanError("network_unavailable")).toMatch(/No connection/);
    expect(humanError("http_503")).toMatch(/trouble/);
    expect(humanError("some_unknown_code")).not.toContain("_");
    expect(humanError("kCLErrorDomain error 0")).toMatch(/GPS/);
    expect(humanError("Capture a photo first")).toBe("Capture a photo first");
    expect(humanError("")).toMatch(/Something went wrong/);
  });
  it("classifies account switch and silent outcomes", () => {
    expect(needsAccountSwitch("driver_not_found")).toBe(true);
    expect(needsAccountSwitch("network_unavailable")).toBe(false);
    expect(isSilentError("photo_cancelled")).toBe(true);
  });
});

describe("canEnterRoute (fail-closed)", () => {
  it("needs API up, auth up and a session", () => {
    expect(canEnterRoute(hs({ api: "down" }), true, false).ok).toBe(false);
    expect(canEnterRoute(hs({ auth: "down" }), true, false).ok).toBe(false);
    expect(canEnterRoute(hs({}), false, false)).toEqual({ ok: false, reason: "Sign in required" });
    expect(canEnterRoute(hs({}), false, true).ok).toBe(true);
    expect(
      canEnterRoute(hs({ auth: "down", error: "driver_onboarding_blocked:docs" }), true, false).ok
    ).toBe(true);
  });
});

describe("mergeOfflineHandshake", () => {
  it("keeps the stop on screen when signal drops mid-route", () => {
    const prev = hs({ online: true, routeId: "r1", stopId: "s1" });
    const merged = mergeOfflineHandshake(prev, hs({ api: "down", routeId: null }), true);
    expect(merged.routeId).toBe("r1");
    expect(merged.api).toBe("down");
  });
  it("applies the fresh snapshot when online or signed out", () => {
    const prev = hs({ online: true, routeId: "r1" });
    expect(mergeOfflineHandshake(prev, hs({ routeId: "r2" }), true).routeId).toBe("r2");
    expect(
      mergeOfflineHandshake(prev, hs({ api: "down", routeId: null }), false).routeId
    ).toBeNull();
  });
});
