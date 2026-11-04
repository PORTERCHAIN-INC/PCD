/** jsxImportSource shim: React's runtime + EN/FR translation of string children and text props. */
import * as R from "react/jsx-runtime";
import { translateProps } from "./translateProps";

export const Fragment = R.Fragment;
export type { JSX } from "react/jsx-runtime";
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type P = any;
export function jsx(type: P, props: P, key?: P) {
  return R.jsx(type, translateProps(type, props), key);
}
export function jsxs(type: P, props: P, key?: P) {
  return R.jsxs(type, translateProps(type, props), key);
}
