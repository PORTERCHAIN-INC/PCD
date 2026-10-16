import { describe, expect, it } from "vitest";
import { contrastRatio, dark, light, type Palette } from "./palette";

// WCAG 2.1 AA: 4.5:1 for body text, 3:1 for large text and UI components.
const TEXT_PAIRS: Array<[keyof Palette, keyof Palette]> = [
  ["primary", "grayBg"],
  ["primary", "white"],
  ["muted", "grayBg"],
  ["muted", "white"],
  ["accentText", "grayBg"],
  ["accentText", "white"],
  ["accentText", "infoBg"],
  ["onAccent", "secondary"],
  ["danger", "white"],
  ["danger", "dangerBg"],
  ["success", "successBg"],
  ["warning", "warningBg"],
  ["onHero", "hero"],
  ["onHeroMuted", "hero"],
  ["muted", "sunken"],
];

describe.each([
  ["light", light],
  ["dark", dark],
])("%s palette", (_name, p) => {
  it.each(TEXT_PAIRS)("%s on %s meets AA (4.5:1)", (fg, bg) => {
    expect(contrastRatio(String(p[fg]), String(p[bg]))).toBeGreaterThanOrEqual(4.5);
  });
});

describe("brand parity", () => {
  it("keeps PorterChain navy, blue and mist", () => {
    expect(light.primary).toBe("#0a1628");
    expect(light.secondary).toBe("#2563eb");
    expect(light.grayBg).toBe("#f0f4f8");
  });
  it("computes the known black/white ratio", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 0);
  });
});
