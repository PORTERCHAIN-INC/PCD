/**
 * Cache Components requires every `generateStaticParams` to return ≥1 sample
 * so the build can validate the route shell. When remote catalogs are empty
 * (local API down), return a single placeholder that the page 404s.
 */
export function ensureStaticParams<T extends Record<string, string>>(
  params: T[],
  fallback: T
): T[] {
  return params.length > 0 ? params : [fallback];
}
