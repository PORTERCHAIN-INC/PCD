/**
 * Device-aware layout: small phones (iPhone SE, 667 pt tall) get tighter type and spacing,
 * big phones and landscape (dashboard mount) get wider gutters, a max content width and
 * two-column layouts where it helps. Everything else stays token-driven.
 */
import { createContext, useContext } from "react";
import { useWindowDimensions } from "react-native";

import { layoutFor, type Layout } from "./layoutFor";

export { layoutFor, type Layout };

export function useLayout(): Layout {
  const { width, height } = useWindowDimensions();
  return layoutFor(width, height);
}

/** True when a tab bar under the screen already pads the bottom safe area. */
export const TabBarBelow = createContext(false);
export const useTabBarBelow = () => useContext(TabBarBelow);
