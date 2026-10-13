/**
 * Device-aware layout: small phones (iPhone SE, 667 pt tall) get tighter type and spacing,
 * big phones and landscape (dashboard mount) get wider gutters, a max content width and
 * two-column layouts where it helps. Everything else stays token-driven.
 */
import { createContext, useContext } from "react";
import { useWindowDimensions } from "react-native";

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

export function useLayout(): Layout {
  const { width, height } = useWindowDimensions();
  return layoutFor(width, height);
}

/** True when a tab bar under the screen already pads the bottom safe area. */
export const TabBarBelow = createContext(false);
export const useTabBarBelow = () => useContext(TabBarBelow);
