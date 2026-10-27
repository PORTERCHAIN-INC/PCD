/** Minimal `process.env` typing for this package's own `tsc --noEmit`; apps bring their own. */
declare const process: {
  env: Record<string, string | undefined>;
};
