import { describe, expect, it, vi } from "vitest";

vi.mock("../api", () => ({}));
vi.mock("../offline", () => ({ runOnlineOrQueue: vi.fn() }));
vi.mock("../ui/PodCapture", () => ({
  emptyPodDraft: () => ({
    photoUrl: null,
    signature: "",
    barcode: "",
    otp: "",
    idType: "",
    idNameMatches: false,
  }),
}));

import { podMissing } from "../hooks/completeStopAction";

const empty = {
  photoUrl: null,
  signature: "",
  barcode: "",
  otp: "",
  idType: "",
  idNameMatches: false,
};

describe("podMissing follows the server's pod_requirements", () => {
  it("server says not enforced → nothing required", () => {
    expect(podMissing(empty, { enforced: false, photo_or_signature: true }, false)).toEqual([]);
  });
  it("server default → photo or signature", () => {
    expect(podMissing(empty, { enforced: true, photo_or_signature: true }, false)).toEqual([
      "photo_or_signature",
    ]);
    expect(
      podMissing({ ...empty, photoUrl: "x" }, { enforced: true, photo_or_signature: true }, false)
    ).toEqual([]);
  });
  it("merchant signature + ID (pharmacy)", () => {
    expect(
      podMissing(
        { ...empty, photoUrl: "x" },
        { enforced: true, photo_or_signature: true, signature: true, id_check: true },
        false
      )
    ).toEqual(["signature", "id_check"]);
  });
  it("OTP from server policy or handshake", () => {
    expect(podMissing({ ...empty, photoUrl: "x" }, { enforced: true, otp: true }, false)).toEqual([
      "otp",
    ]);
    expect(podMissing({ ...empty, photoUrl: "x" }, { enforced: true }, true)).toEqual(["otp"]);
  });
  it("no requirements loaded yet → safe server default, not 'ready'", () => {
    expect(podMissing(empty, null, false)).toEqual(["photo_or_signature"]);
  });
});
