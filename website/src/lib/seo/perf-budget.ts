/**
 * Core Web Vitals 2.0 perf budgets for RUM reporting (Wave 10 w10-1).
 * INP good ≤200 ms, needs-improvement ≤500 ms (Google CWV thresholds).
 */

export const PERF_BUDGET_INP_GOOD_MS = 200;
export const PERF_BUDGET_INP_POOR_MS = 500;
export const PERF_BUDGET_LCP_GOOD_MS = 2500;
export const PERF_BUDGET_CLS_GOOD = 0.1;

export type PageRouteClass = "business" | "matrix" | "other";

const MATRIX_CITY_SLUGS = new Set([
  "toronto",
  "mississauga",
  "brampton",
  "vaughan",
  "oakville",
  "oshawa",
  "kitchener-waterloo",
  "kitchener",
  "hamilton",
  "london",
  "st-catharines",
  "niagara",
]);

const LOCALE_HUB_SLUGS = new Set([
  "business",
  "contact",
  "company",
  "customers",
  "developers",
  "enterprise",
  "faq",
  "guides",
  "compare",
  "platform",
  "solutions",
  "trust",
  "track",
  "blog",
  "service-areas",
  "industry",
  "how-porterchain-works",
  "sign-in",
  "sign-up",
]);

/** Classify pathname for perf segmentation (matrix landings vs /business). */
export function classifyPageRoute(pathname: string): PageRouteClass {
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length === 0) return "other";

  const offset = parts[0] === "en" || parts[0] === "fr" ? 1 : 0;
  const segments = parts.slice(offset);

  if (segments[0] === "business" || segments.includes("business")) return "business";

  if (segments[0] === "service-areas" && segments.length >= 2) return "matrix";

  if (
    segments.length >= 2 &&
    MATRIX_CITY_SLUGS.has(segments[0]!) &&
    !LOCALE_HUB_SLUGS.has(segments[1]!)
  ) {
    return "matrix";
  }

  return "other";
}

export function isOverPerfBudget(metricName: "INP" | "LCP" | "CLS", value: number): boolean {
  if (metricName === "INP") return value > PERF_BUDGET_INP_GOOD_MS;
  if (metricName === "LCP") return value > PERF_BUDGET_LCP_GOOD_MS;
  return value > PERF_BUDGET_CLS_GOOD;
}
