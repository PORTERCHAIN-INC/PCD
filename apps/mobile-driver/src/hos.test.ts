import { describe, expect, it, vi } from "vitest";

vi.mock("./offline", () => ({ enqueueOfflineAction: vi.fn(), newClientId: () => "cid-1" }));

import { hosPayload, statusFromSpeed } from "./hos";

describe("phone HOS log", () => {
  it("switches to driving above 10 km/h and back", () => {
    expect(statusFromSpeed("on_duty", 3)).toBe("driving"); // 10.8 km/h
    expect(statusFromSpeed("driving", 2)).toBe("on_duty");
    expect(statusFromSpeed("driving", 5)).toBeNull();
    expect(statusFromSpeed("off_duty", 20)).toBeNull();
  });
  it("stamps the phone clock at the event", () => {
    const at = new Date("2026-10-29T12:00:00Z");
    expect(hosPayload("on_duty", { other_operator_today: true }, at)).toEqual({
      client_id: "cid-1",
      status: "on_duty",
      at: "2026-10-29T12:00:00.000Z",
      other_operator_today: true,
    });
  });
});
