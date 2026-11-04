import * as R from "react/jsx-dev-runtime";
import { translateProps } from "./translateProps";

export const Fragment = R.Fragment;
export type { JSX } from "react/jsx-dev-runtime";
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type P = any;
export function jsxDEV(type: P, props: P, key: P, isStatic: P, source: P, self: P) {
  return R.jsxDEV(type, translateProps(type, props), key, isStatic, source, self);
}
