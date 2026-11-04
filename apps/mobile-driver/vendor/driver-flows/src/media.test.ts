import { describe, expect, it } from "vitest";
import { isPngDataUrl, mediaClient, signatureReady, strokesToPath } from "./media";

const line = (n: number, w = 100) =>
  Array.from({ length: n }, (_, i) => ({ x: (i * w) / n, y: 10 }));

describe("signature media", () => {
  it("needs real ink", () => {
    expect(signatureReady([])).toBe(false);
    expect(signatureReady([line(3)])).toBe(false);
    expect(signatureReady([line(10, 5)])).toBe(false);
    expect(signatureReady([line(10)])).toBe(true);
  });
  it("checks data urls and paths", () => {
    expect(isPngDataUrl("data:image/png;base64,iVBORw0KGgo=")).toBe(true);
    expect(isPngDataUrl("data:image/jpeg;base64,abc")).toBe(false);
    expect(
      strokesToPath([
        [
          { x: 1, y: 2 },
          { x: 3, y: 4 },
        ],
      ])
    ).toBe("M1.0,2.0 L3.0,4.0");
  });
  it("posts to the upload routes and rejects bad signatures", async () => {
    const calls: [string, unknown][] = [];
    const m = mediaClient(async (p, b) => {
      calls.push([p, b]);
      return { key: "k" } as never;
    });
    await m.signature("data:image/png;base64,iVBORw0KGgo=", "Ann");
    await m.photo(new Blob(["x"]));
    expect(calls[0][0]).toBe("/v1/media/signature");
    expect(JSON.parse(calls[0][1] as string)).toEqual({
      data_url: "data:image/png;base64,iVBORw0KGgo=",
      signer_name: "Ann",
    });
    expect(calls[1][0]).toBe("/v1/media/photo");
    await expect(m.signature("nope", "Ann")).rejects.toThrow("signature_invalid");
    await expect(m.signature("data:image/png;base64,iVBORw0KGgo=", " ")).rejects.toThrow(
      "signer_name_required"
    );
    await m.photoDataUrl("data:image/jpeg;base64,/9j/");
    expect(calls[2][0]).toBe("/v1/media/photo-data");
  });
});

import { strokesToPngDataUrl } from "./media";
import { inflateSync } from "node:zlib";

describe("strokesToPngDataUrl", () => {
  it("makes a valid PNG with ink", () => {
    const url = strokesToPngDataUrl([line(20)], 120, 40);
    expect(isPngDataUrl(url)).toBe(true);
    const buf = Buffer.from(url.split(",")[1], "base64");
    expect([...buf.subarray(0, 8)]).toEqual([137, 80, 78, 71, 13, 10, 26, 10]);
    const idatLen = buf.readUInt32BE(33);
    const raw = inflateSync(buf.subarray(41, 41 + idatLen));
    expect(raw.length).toBe(121 * 40);
    expect(raw.includes(0x00, 1)).toBe(true);
    expect(strokesToPngDataUrl([line(40, 300)]).length * 0.75).toBeLessThan(300_000);
  });
});
