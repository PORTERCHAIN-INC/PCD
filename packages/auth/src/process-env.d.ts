/**
 * Minimal `process.env` typing for this package's own `tsc --noEmit` run.
 *
 * `devBypass.ts` reads build-time variables and must stay dependency-free so the
 * Edge runtime can import it, so the package does not pull in `@types/node`.
 * Consuming apps already have their own `process` typings.
 */
declare const process: {
  env: Record<string, string | undefined>;
};
