import type { ComponentType } from "react";

/** Navigation screen prop typing helper for lazy-loaded screens. */
export function asNavScreen<P extends object>(screen: ComponentType<P>): ComponentType<P> {
  return screen as ComponentType<P>;
}
