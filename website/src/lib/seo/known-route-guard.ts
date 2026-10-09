import {
  getDeliveryArea,
  getDeliveryVertical,
  isFitCombination,
} from "@/lib/seo/delivery-programmatic";
import { isValidNicheSlug } from "@/lib/seo/niche-landing";
import { isValidServiceAreaSlug } from "@/lib/seo/service-areas";
import { AUTHORITY_PAGES } from "@/lib/seo/content/authority-pages";
import { COMPARISON_PAGES } from "@/lib/seo/content/comparison-pages";
import { FAQ_CLUSTERS } from "@/lib/seo/content/faq-clusters";
import { listPublicSuccessStories } from "@/lib/seo/content/success-stories";

/**
 * Valid slugs for static content families (English source of truth). FR pages without a
 * translation still 404 in-page; unknown slugs are rejected here before rendering.
 * Blog posts are API-backed (scheduled publishing), so /blog/[slug] is not guarded here.
 */
const STATIC_SLUG_FAMILIES: Record<string, ReadonlySet<string>> = {
  faq: new Set(FAQ_CLUSTERS.map((c) => c.slug)),
  guides: new Set(AUTHORITY_PAGES.map((p) => p.slug)),
  compare: new Set(COMPARISON_PAGES.map((p) => p.slug)),
  "success-stories": new Set(listPublicSuccessStories().map((s) => s.slug)),
};

/**
 * Real 404s for programmatic routes whose valid params are known statically.
 *
 * With `cacheComponents`, unknown params render on demand and `notFound()` fires after the
 * shell has streamed, so the response is a 200 with an injected noindex (a soft 404 —
 * readiness audit #14). Middleware rejects the bad URL before rendering instead.
 * Returns true when the path belongs to a guarded family AND its params are invalid.
 */
export function isKnownInvalidRoute(pathname: string, locales: readonly string[]): boolean {
  const parts = pathname.replace(/\/+$/, "").split("/").filter(Boolean);
  if (parts.length < 3 || !locales.includes(parts[0])) return false;
  const [, family, a, b, ...rest] = parts;
  const seg = (s: string) => decodeURIComponent(s);

  if (family === "delivery") {
    if (rest.length) return true;
    const vertical = getDeliveryVertical(seg(a));
    if (!vertical) return true;
    if (b === undefined) return false;
    const area = getDeliveryArea(seg(b));
    return !area || !isFitCombination(vertical, area);
  }
  const staticSlugs = STATIC_SLUG_FAMILIES[family];
  if (staticSlugs) return b !== undefined || !staticSlugs.has(seg(a));
  if (family === "industry" && b === undefined) return !isValidNicheSlug(seg(a));
  if (family === "service-areas" && b === undefined) return !isValidServiceAreaSlug(seg(a));
  return false;
}
