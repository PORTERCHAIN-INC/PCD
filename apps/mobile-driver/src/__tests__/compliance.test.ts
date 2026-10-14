import { beforeEach, describe, expect, it, vi } from "vitest";
import { asyncStorageMock, resetNative } from "./nativeMocks";
import { NetworkError } from "../netErrors";

vi.mock("@react-native-async-storage/async-storage", () => ({ default: asyncStorageMock }));
vi.mock("react-native", () => ({ Alert: { alert: vi.fn() }, Platform: { OS: "android" } }));
const api = vi.hoisted(() => ({
  fetchGpsStatus: vi.fn(),
  fetchMonitoringPolicy: vi.fn(),
  ackMonitoringPolicy: vi.fn(async () => ({})),
  sendGpsConsent: vi.fn(async (_accepted: boolean) => ({ enabled: true, message: "" })),
}));
vi.mock("../api", () => api);
vi.mock("../location", () => ({ refreshGpsPolicy: vi.fn(async () => true) }));

import {
  agreeToMonitoring,
  checkCompliance,
  resendPendingConsent,
  withdrawMonitoring,
} from "../compliance";
import { readLocationConsent } from "../consent";

const policy = {
  title: "Electronic Monitoring Policy",
  version: "2026-10",
  date: "",
  sections: [],
  acknowledged: false,
};

beforeEach(() => {
  resetNative();
  api.ackMonitoringPolicy.mockResolvedValue({});
  api.sendGpsConsent.mockResolvedValue({ enabled: true, message: "" });
});

describe("GPS consent is recorded on the server (policy 2026-10)", () => {
  it("server says consent required → needed, even if the phone has an old local yes", async () => {
    api.fetchGpsStatus.mockResolvedValue({ enabled: false, message: "x", consent_required: true });
    api.fetchMonitoringPolicy.mockResolvedValue(policy);
    const local = {
      version: 2,
      agreedAt: "2026-10-01T00:00:00Z",
      policyVersion: "2026-10",
      serverSynced: true,
    };
    expect((await checkCompliance(local)).needed).toBe(true);
  });

  it("agree → policy ack + gps-consent(true) + local copy marked synced", async () => {
    const saved = await agreeToMonitoring(policy);
    expect(api.ackMonitoringPolicy).toHaveBeenCalledTimes(1);
    expect(api.sendGpsConsent).toHaveBeenCalledWith(true);
    expect(saved).toMatchObject({ policyVersion: "2026-10", serverSynced: true });
  });

  it("agree offline → kept locally as unsynced and re-sent on the next open", async () => {
    api.ackMonitoringPolicy.mockRejectedValueOnce(new NetworkError("network_unavailable"));
    expect(await agreeToMonitoring(policy)).toMatchObject({ serverSynced: false });
    const again = await resendPendingConsent();
    expect(again).toMatchObject({ serverSynced: true });
    expect(api.sendGpsConsent).toHaveBeenCalledWith(true);
  });

  it("server rejection is shown, not hidden", async () => {
    api.sendGpsConsent.mockRejectedValueOnce(
      Object.assign(new Error("driver_not_approved"), { kind: "api" })
    );
    await expect(agreeToMonitoring({ ...policy, acknowledged: true })).rejects.toThrow(
      "driver_not_approved"
    );
    expect(await readLocationConsent()).toBeNull();
  });

  it("withdraw → gps-consent(false) and local record gone", async () => {
    await agreeToMonitoring(policy);
    await withdrawMonitoring();
    expect(api.sendGpsConsent).toHaveBeenLastCalledWith(false);
    expect(await readLocationConsent()).toBeNull();
  });
});
