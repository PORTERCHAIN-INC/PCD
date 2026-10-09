import { resolveUrlPolicy } from "./url-policy";
import { splitTrackingParams } from "./tracking-params";

/**
 * Canonical form of an internal href for a next-intl Link (which adds the locale itself).
 * Returns null for external / non-path hrefs. `href` in the result has NO locale prefix.
 */
export function canonicalInternalHref(
  href: string,
  locale: string
): { href: string; locale: string; from?: string } | null {
  if (!href.startsWith("/") || href.startsWith("//")) return null;
  const { href: clean, from } = splitTrackingParams(href);
  const hashIdx = clean.indexOf("#");
  const hash = hashIdx >= 0 ? clean.slice(hashIdx) : "";
  const noHash = hashIdx >= 0 ? clean.slice(0, hashIdx) : clean;
  const qIdx = noHash.indexOf("?");
  const query = qIdx >= 0 ? noHash.slice(qIdx) : "";
  let path = qIdx >= 0 ? noHash.slice(0, qIdx) : noHash;

  let linkLocale = locale;
  const prefixed = path.match(/^\/(en|fr)(\/.*)?$/);
  if (prefixed) {
    linkLocale = prefixed[1];
    path = prefixed[2] ?? "/";
  }
  const full = `/${linkLocale}${path === "/" ? "" : path}`;
  const policy = resolveUrlPolicy(full, query);
  if (policy.action === "redirect") {
    const target = policy.location;
    const m = target.match(/^\/(en|fr)(\/[^?#]*)?([?#].*)?$/);
    if (m) {
      return { href: `${m[2] ?? "/"}${m[3] ?? ""}`, locale: m[1], from };
    }
  }
  return { href: `${path}${query}${hash}`, locale: linkLocale, from };
}
