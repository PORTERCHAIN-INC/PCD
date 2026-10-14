import { describe, expect, it, vi } from "vitest";
vi.mock("react-native", () => ({ Platform: { OS: "ios" }, AppState: {} }));
const gps = vi.fn();
vi.mock("../api", () => ({
  fetchGpsStatus: () => gps(),
  pingLocation: vi.fn(),
  setAvailability: vi.fn(),
}));
vi.mock("../offline", () => ({ enqueueGpsPing: vi.fn() }));
vi.mock("../consent", () => ({ readLocationConsent: vi.fn() }));
vi.mock("expo-location", () => ({
  hasStartedLocationUpdatesAsync: vi.fn(),
  stopLocationUpdatesAsync: vi.fn(),
}));
vi.mock("expo-task-manager", () => ({ isTaskRegisteredAsync: vi.fn(), defineTask: vi.fn() }));
import { noFixState, onGpsPolicyEnabled, readPosition, refreshGpsPolicy } from "../location";

const fix = {
  coords: { latitude: 43.5, longitude: -79.8, accuracy: 10, heading: null, speed: null },
};
const loc = (o: Record<string, unknown>) => ({ Accuracy: { Balanced: 3 }, ...o }) as never;

describe("location: permission granted but no fix", () => {
  it("falls back to a recent cached fix", async () => {
    const L = loc({
      getCurrentPositionAsync: vi.fn().mockRejectedValue(new Error("kCLErrorDomain 0")),
      getLastKnownPositionAsync: vi.fn().mockResolvedValue(fix),
    });
    expect(await readPosition(L)).toBe(fix);
  });
  it("says 'finding GPS', not 'location is off', when services are on", async () => {
    const s = await noFixState(loc({ hasServicesEnabledAsync: vi.fn().mockResolvedValue(true) }));
    expect(s.kind).toBe("searching");
  });
  it("names Location Services when they are off", async () => {
    const s = await noFixState(loc({ hasServicesEnabledAsync: vi.fn().mockResolvedValue(false) }));
    expect(s.kind).toBe("denied");
    expect(s.detail).toMatch(/Location Services/);
  });
});

describe("location: consent turns GPS back on", () => {
  it("notifies listeners so the app asks iOS for permission right away", async () => {
    const hit = vi.fn();
    onGpsPolicyEnabled(hit);
    gps.mockResolvedValueOnce({ enabled: false, message: "consent needed" });
    await refreshGpsPolicy();
    expect(hit).not.toHaveBeenCalled();
    gps.mockResolvedValueOnce({ enabled: true, message: null });
    await refreshGpsPolicy();
    expect(hit).toHaveBeenCalledTimes(1);
  });
});
