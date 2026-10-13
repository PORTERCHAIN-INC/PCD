import { describe, expect, it, vi } from "vitest";

vi.mock("react-native", () => ({
  AppState: { currentState: "active" },
  Platform: { OS: "android" },
  Linking: {},
}));
vi.mock("expo-haptics", () => ({}));
vi.mock("../api", () => ({}));
vi.mock("../offline", () => ({ newClientId: () => "c", runOnlineOrQueue: vi.fn() }));

import { applyLocalCheckin, etaSecondsFrom } from "../hooks/useDispatchRoute";
import { navigationLinks } from "../maps";
import { distanceM, etaCountdown, insideGeofence, money } from "../smart/geo";
import type { DispatchRoute, DispatchStop } from "../dispatchRoute";

const stop = (id: string, status: DispatchStop["status"] = "pending"): DispatchStop => ({
  keys: [id],
  order_id: id,
  order_number: id,
  kind: "drop",
  status,
  address: "1 King St W, Toronto",
  lat: 43.6487,
  lng: -79.3774,
  boxes: 1,
  needs_pod: true,
  notes: null,
  eta_s: 0,
});

describe("geo + ETA", () => {
  it("distance Milton → downtown Toronto is ~45 km", () => {
    const d = distanceM({ lat: 43.5183, lng: -79.8774 }, { lat: 43.6487, lng: -79.3774 });
    expect(d).toBeGreaterThan(40_000);
    expect(d).toBeLessThan(45_000);
  });

  it("geofence: inside 100 m at parking speed counts; driving past or a bad fix does not", () => {
    const s = { lat: 43.6487, lng: -79.3774 };
    const near = { lat: 43.6492, lng: -79.3774 }; // ~55 m
    expect(insideGeofence({ ...near, accuracy: 10, speed: 1 }, s)).toBe(true);
    expect(insideGeofence({ ...near, accuracy: 10, speed: 12 }, s)).toBe(false);
    expect(insideGeofence({ ...near, accuracy: 150, speed: 0 }, s)).toBe(false);
    expect(insideGeofence({ lat: 43.652, lng: -79.3774, accuracy: 5, speed: 0 }, s)).toBe(false);
  });

  it("countdown copy", () => {
    expect(etaCountdown(10_000, 0)).toBe("Now");
    expect(etaCountdown(45_000, 0)).toBe("45 s");
    expect(etaCountdown(4 * 60_000, 0)).toBe("4 min");
    expect(etaCountdown(65 * 60_000, 0)).toBe("1 h 05");
    expect(money(13560)).toBe("$135.60");
    expect(money(null)).toBe("—");
  });

  it("ETA from live GPS uses road-distance estimate, none without a fix", () => {
    expect(etaSecondsFrom(null, stop("a"))).toBeNull();
    const eta = etaSecondsFrom({ lat: 43.6577, lng: -79.3774 }, stop("a")); // ~1 km
    expect(eta).toBeGreaterThan(120);
    expect(eta).toBeLessThan(240);
  });
});

describe("offline-first check-in", () => {
  it("moves to the next stop locally when queued", () => {
    const route: DispatchRoute = {
      id: "r",
      vehicle_class: "van",
      stops: [stop("a"), stop("b")],
      next_index: 0,
      done: 0,
      total: 2,
    };
    const arrived = applyLocalCheckin(route, ["a"], "arrived");
    expect(arrived.stops[0].status).toBe("arrived");
    expect(arrived.next_index).toBe(0);
    const delivered = applyLocalCheckin(arrived, ["a"], "delivered");
    expect(delivered.next_index).toBe(1);
    expect(delivered.done).toBe(1);
    const last = applyLocalCheckin(delivered, ["b"], "failed");
    expect(last.next_index).toBeNull();
    expect(last.done).toBe(2);
  });
});

describe("one-tap navigate", () => {
  it("Android: Google Maps turn-by-turn first, then any maps app, then web", () => {
    const links = navigationLinks({ lat: 43.6, lng: -79.3 }, "android");
    expect(links[0]).toBe("google.navigation:q=43.6,-79.3&mode=d");
    expect(links[1]).toMatch(/^geo:/);
    expect(links.at(-1)).toMatch(/^https:\/\/www\.google\.com\/maps\/dir/);
  });
  it("iOS: Google Maps if installed, else Apple Maps; API navigation_url wins", () => {
    expect(navigationLinks({ address: "1 King St" }, "ios")[0]).toMatch(/^comgooglemaps:/);
    expect(
      navigationLinks({ navigationUrl: "https://nav.example/x", lat: 1, lng: 2 }, "ios")[0]
    ).toBe("https://nav.example/x");
    expect(navigationLinks({}, "ios")).toEqual([]);
  });
});
