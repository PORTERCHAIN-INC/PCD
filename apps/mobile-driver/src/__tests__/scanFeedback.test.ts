import { describe, expect, it, vi } from "vitest";

vi.mock("expo-audio", () => ({
  createAudioPlayer: () => ({ seekTo: async () => {}, play: () => {} }),
}));
vi.mock("expo-haptics", () => ({
  impactAsync: async () => {},
  notificationAsync: async () => {},
  ImpactFeedbackStyle: {},
  NotificationFeedbackType: {},
}));
vi.mock("../settings", () => ({ getSettings: () => ({ haptics: true }) }));

import { makeDeduper, scanFeedback } from "../scanFeedback";

describe("camera scan dedupe", () => {
  it("counts a label once while it stays in frame, again after the window", () => {
    const fresh = makeDeduper(2500);
    expect(fresh("PC1.A.B", 0)).toBe(true);
    expect(fresh("PC1.A.B", 500)).toBe(false);
    expect(fresh("PC1.C.D", 600)).toBe(true);
    expect(fresh("PC1.A.B", 3200)).toBe(true);
  });

  it("feedback never throws", () => {
    for (const o of ["ok", "done", "queued", "warn", "error"] as const) {
      expect(() => scanFeedback(o)).not.toThrow();
    }
  });
});
