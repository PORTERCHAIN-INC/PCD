/** Pure breakpoint logic (unit-tested; no React Native import). */
export type Layout = {
  width: number;
  height: number;
  landscape: boolean;
  /** iPhone SE / small Android: height < 700 pt (portrait) or width < 360. */
  compact: boolean;
  /** Pro Max / big Android / tablets-in-portrait. */
  roomy: boolean;
  /** Horizontal gutter. */
  gutter: number;
  /** Max readable content width (centred on wide screens). */
  maxContent: number;
  /** Multiplier for hero/display type. */
  scale: number;
};

export function layoutFor(width: number, height: number): Layout {
  const landscape = width > height;
  const short = Math.min(width, height);
  const long = Math.max(width, height);
  const compact = !landscape && (long < 700 || short < 360);
  const roomy = !landscape && short >= 414 && long >= 880;
  return {
    width,
    height,
    landscape,
    compact,
    roomy,
    gutter: compact ? 14 : roomy ? 22 : landscape ? 24 : 18,
    maxContent: landscape ? 1100 : 640,
    scale: compact ? 0.86 : roomy ? 1.08 : landscape ? 0.92 : 1,
  };
}
