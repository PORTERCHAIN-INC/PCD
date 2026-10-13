import { describe, expect, it, vi } from "vitest";
import { asyncStorageMock } from "./nativeMocks";

vi.mock("@react-native-async-storage/async-storage", () => ({ default: asyncStorageMock }));
vi.mock("react-native", () => ({ Platform: { OS: "ios" }, Linking: { openURL: vi.fn() } }));

import type { DriverDocument } from "../api";
import { agoLabel, shouldPersist } from "../data/keys";
import { docAlerts, docHealth, docLine, optimisticUpload, sortDocs } from "../docs";
import { tr } from "../i18n";
import { navigationLinks } from "../maps";
import { DEFAULT_SETTINGS, getSettings, sanitize, setSettings, toServer } from "../settings";
import { gpsMode } from "../smart/route";

const NOW = Date.parse("2026-10-13T12:00:00");
const doc = (o: Partial<DriverDocument>): DriverDocument => ({
  type: "license",
  label: "Driver License",
  status: "verified",
  verified: true,
  has_file: true,
  url: null,
  uploaded_at: null,
  expires_at: null,
  rejection_reason: null,
  ...o,
});

describe("documents", () => {
  it("classifies expiry and status", () => {
    expect(docHealth(doc({ expires_at: "2026-10-01" }), NOW)).toBe("expired");
    expect(docHealth(doc({ expires_at: "2026-11-01" }), NOW)).toBe("expiring");
    expect(docHealth(doc({ expires_at: "2027-06-01" }), NOW)).toBe("ok");
    expect(docHealth(doc({ status: "missing", verified: false, has_file: false }), NOW)).toBe(
      "missing"
    );
    expect(docHealth(doc({ status: "pending_review", verified: false }), NOW)).toBe("review");
    expect(docHealth(doc({ status: "rejected" }), NOW)).toBe("rejected");
  });
  it("writes one plain line", () => {
    expect(docLine(doc({ expires_at: "2026-10-20" }), NOW)).toBe("Expires in 7 days");
    expect(docLine(doc({ status: "missing", verified: false, has_file: false }), NOW)).toBe(
      "Required · not uploaded"
    );
    expect(
      docLine(
        doc({ type: "work_permit", status: "missing", verified: false, has_file: false }),
        NOW
      )
    ).toBe("Not uploaded");
  });
  it("sorts urgent first and counts alerts", () => {
    const docs = [
      doc({ type: "abstract" }),
      doc({ type: "insurance", expires_at: "2026-10-01" }),
      doc({ type: "work_permit", status: "missing", verified: false, has_file: false }),
      doc({ type: "vehicle_registration", expires_at: "2026-10-30" }),
    ];
    expect(sortDocs(docs, NOW).map((d) => d.type)).toEqual([
      "insurance",
      "work_permit",
      "vehicle_registration",
      "abstract",
    ]);
    expect(docAlerts(docs, NOW)).toBe(2); // expired insurance + expiring registration (optional permit not counted)
  });
  it("optimistic upload flips to in review", () => {
    const out = optimisticUpload(
      [doc({ status: "rejected", rejection_reason: "blurry" })],
      "license",
      "2028-01-01"
    );
    expect(out[0]).toMatchObject({
      status: "pending_review",
      rejection_reason: null,
      expires_at: "2028-01-01",
    });
  });
});

describe("cache", () => {
  it("persists only allow-listed successful queries", () => {
    expect(shouldPersist({ queryKey: ["documents"], state: { status: "success" } })).toBe(true);
    expect(shouldPersist({ queryKey: ["documents"], state: { status: "error" } })).toBe(false);
    expect(shouldPersist({ queryKey: ["contact", "o1"], state: { status: "success" } })).toBe(
      false
    );
  });
  it("labels age", () => {
    expect(agoLabel(NOW - 2_000, NOW)).toBe("now");
    expect(agoLabel(NOW - 12_000, NOW)).toBe("12s ago");
    expect(agoLabel(NOW - 4 * 60_000, NOW)).toBe("4m ago");
    expect(agoLabel(0, NOW)).toBe("");
  });
});

describe("settings", () => {
  it("drops bad values and keeps auto nav local", () => {
    expect(
      sanitize({ nav_app: "bing", voice: "yes", text_scale: 1.15, battery_saver_pct: 99 })
    ).toEqual({ text_scale: 1.15 });
    expect(toServer({ nav_app: "auto", voice: false })).toEqual({ voice: false });
    expect(toServer({ nav_app: "waze" })).toEqual({ nav_app: "waze" });
  });
  it("chosen nav app goes first", () => {
    setSettings({ nav_app: "waze" });
    expect(navigationLinks({ lat: 43.6, lng: -79.4 }, "ios")[0]).toBe(
      "https://waze.com/ul?ll=43.6,-79.4&navigate=yes"
    );
    setSettings({ nav_app: "auto" });
    expect(navigationLinks({ lat: 43.6, lng: -79.4 }, "ios")[0]).toContain("comgooglemaps://");
    expect(getSettings().nav_app).toBe(DEFAULT_SETTINGS.nav_app);
  });
  it("battery threshold is configurable; 0 = off", () => {
    expect(gpsMode(0.25, false, 30)).toBe("saver");
    expect(gpsMode(0.05, false, 0)).toBe("high");
  });
  it("speaks French", () => expect(tr("settings", "fr")).toBe("Paramètres"));
});
