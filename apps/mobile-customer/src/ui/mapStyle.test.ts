import { describe, expect, it } from "vitest";
import { boundsOf, porterchainNativeStyle } from "./mapStyle";

describe("native map style", () => {
  it("reads self-hosted PMTiles, no vendor key", () => {
    const s = porterchainNativeStyle("light", "https://tiles.example.test");
    const src = s.sources.protomaps as { url: string };
    expect(src.url).toBe("pmtiles://https://tiles.example.test/gta-150km.pmtiles");
    expect(s.sprite).toBe("https://tiles.example.test/sprites/v4/light");
    expect(s.layers.length).toBeGreaterThan(10);
    expect(JSON.stringify(s)).not.toMatch(/key=|access_token/);
  });

  it("dark scheme uses dark sprite", () => {
    expect(porterchainNativeStyle("dark", "https://t").sprite).toBe("https://t/sprites/v4/dark");
  });

  it("bounds fit all points and pad a single point", () => {
    expect(boundsOf([])).toBeNull();
    const b = boundsOf([
      { latitude: 43.6, longitude: -79.5 },
      { latitude: 43.8, longitude: -79.2 },
    ]);
    expect(b).toEqual([-79.5, 43.6, -79.2, 43.8]);
    const one = boundsOf([{ latitude: 43.65, longitude: -79.38 }])!;
    expect(one[2] - one[0]).toBeCloseTo(0.02);
  });
});
