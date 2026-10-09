/**
 * Internal links must point at canonical URLs. `?from=` (which CTA was clicked) created
 * hundreds of parameter duplicates in Search Console ("Alternate page with proper canonical",
 * "Duplicate without user-selected canonical"). The value now travels in sessionStorage via
 * the Link click handler (rememberQuoteIntent) instead of the URL.
 */
export const LINK_TRACKING_PARAMS = ["from"] as const;

export function splitTrackingParams(href: string): { href: string; from?: string } {
  const qIdx = href.indexOf("?");
  if (qIdx < 0) return { href };
  const hashIdx = href.indexOf("#", qIdx);
  const base = href.slice(0, qIdx);
  const query = href.slice(qIdx + 1, hashIdx >= 0 ? hashIdx : undefined);
  const hash = hashIdx >= 0 ? href.slice(hashIdx) : "";
  const params = new URLSearchParams(query);
  const from = params.get("from") ?? undefined;
  if (from === undefined) return { href };
  for (const key of LINK_TRACKING_PARAMS) params.delete(key);
  const rest = params.toString();
  return { href: `${base}${rest ? `?${rest}` : ""}${hash}`, from };
}
