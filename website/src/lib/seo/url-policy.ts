/**
 * Single-hop URL policy for the public site (GSC "Page indexing" clean-up, Oct 2026).
 *
 * Every legacy / duplicate / gated URL resolves to ONE final destination in ONE 301:
 *   1. normalise: trailing slash, duplicate slashes, /index.html
 *   2. legacy prefixes: /ca/en → /en, /ca/fr-ca → /fr, doubled locales (/en/en, /fr/fr),
 *      locale-less legacy paths (/pricing, /blog/x) → /en/...
 *   3. renamed / retired slugs from the registry in ./redirects.ts (applied to a fixed point,
 *      so registry chains collapse into one hop)
 *   4. programmatic families (city × segment, delivery, industry, service areas, campaigns,
 *      FAQ/guides/compare/…): anything not in the build-time indexable manifest goes to its
 *      nearest indexable parent instead of rendering a soft-404 / noindex page
 * Junk URLs (crawler artefacts) get 410. Truly unknown paths fall through to a real 404.
 *
 * Pure function — no I/O — so it runs in middleware and in unit tests.
 */
import indexablePaths from "../../generated/indexable-paths.json";
import { WEBSITE_REDIRECTS } from "./redirects";

export const POLICY_LOCALES = ["en", "fr"] as const;
type PolicyLocale = (typeof POLICY_LOCALES)[number];

const INDEXABLE = new Set<string>(indexablePaths as string[]);

export function isIndexablePath(path: string): boolean {
  return INDEXABLE.has(path);
}

/** Top-level directories under app/[locale] (kept in sync by url-policy test). */
export const LOCALE_APP_SECTIONS = new Set([
  "accessibility",
  "authors",
  "blog",
  "book",
  "box-truck-delivery",
  "business",
  "campaigns",
  "careers",
  "cargo-van-delivery",
  "company",
  "compare",
  "contact",
  "cookies",
  "delivery",
  "delivery-cost-calculator",
  "developers",
  "email-preferences",
  "enterprise",
  "facts",
  "faq",
  "guides",
  "industry",
  "integrations",
  "login",
  "newsletter",
  "onboarding-education",
  "page-not-found",
  "pickup-truck-delivery",
  "platform",
  "privacy",
  "quote",
  "research",
  "sedan-delivery",
  "service-areas",
  "sign-up",
  "terms",
  "track",
  "trade-van-delivery",
  "trust",
  "unsubscribe",
  "vehicle-partner",
  "vehicles",
]);

/** City URL slugs served by app/[locale]/[city]/[industrySlug] → service-area slug. */
export const POLICY_CITY_TO_AREA: Record<string, string> = {
  toronto: "toronto",
  mississauga: "mississauga",
  brampton: "brampton",
  vaughan: "vaughan",
  oakville: "oakville",
  oshawa: "oshawa",
  kitchener: "kitchener-waterloo",
  hamilton: "hamilton",
  london: "london",
  "st-catharines": "st-catharines",
  niagara: "niagara",
  // legacy city slugs seen in Search Console / old sitemaps
  "kitchener-waterloo": "kitchener-waterloo",
  markham: "markham",
  burlington: "burlington",
  ajax: "ajax",
  pickering: "pickering",
  cambridge: "cambridge",
  guelph: "guelph",
  waterloo: "kitchener-waterloo",
};

/** City segment → the strongest topical hub when the city page itself is not indexable. */
const CITY_SEGMENT_HUB: Record<string, string[]> = {
  "construction-materials-delivery": ["industry/construction-materials", "delivery/construction"],
  "electrical-delivery": ["industry/electrical-distribution", "delivery/construction"],
  "plumbing-supply-delivery": ["industry/plumbing-supply", "delivery/construction"],
  "coffee-roaster-delivery": ["industry/coffee-roasters", "campaigns/coffee-roasters"],
  "pharmacy-delivery": ["industry/pharmacy-medical", "campaigns/pharmacy-medical"],
  "cosmetics-delivery": ["industry/cosmetics", "campaigns/cosmetics"],
  "chocolate-delivery": ["industry/chocolate"],
  "lab-sample-delivery": ["industry/lab-sample-delivery"],
  "ecommerce-delivery": ["industry/ecommerce"],
  "sedan-delivery": ["sedan-delivery", "vehicles"],
  "suv-delivery": ["sedan-delivery", "vehicles"],
  "trade-van-delivery": ["trade-van-delivery", "vehicles"],
  "pickup-truck-delivery": ["pickup-truck-delivery", "vehicles"],
  "cargo-van-delivery": ["cargo-van-delivery", "vehicles"],
  "box-truck-delivery": ["box-truck-delivery", "vehicles"],
  "same-day-delivery": ["delivery"],
  "local-courier": ["delivery"],
  "last-mile-delivery": ["delivery"],
  "on-demand-delivery": ["delivery"],
  "b2b-delivery": ["business"],
  "furniture-delivery": ["delivery/furniture"],
  "appliance-delivery": ["delivery/furniture"],
  "recurring-delivery": ["campaigns/recurring-delivery", "platform"],
};

/** Legacy /delivery/{vertical}/{area} slugs (2026 matrix) → current matrix / industry pages. */
const DELIVERY_VERTICAL_ALIAS: Record<string, string[]> = {
  "pharmacy-medical": ["delivery/pharmacy", "industry/pharmacy-medical"],
  "lab-sample-delivery": ["delivery/pharmacy", "industry/lab-sample-delivery"],
  chocolate: ["industry/chocolate", "delivery/shopify-merchants"],
  "coffee-roasters": ["industry/coffee-roasters", "delivery/warehouses"],
  cosmetics: ["industry/cosmetics", "delivery/shopify-merchants"],
  "construction-materials": ["delivery/construction"],
  "electrical-distribution": ["delivery/construction"],
  "plumbing-supply": ["delivery/construction"],
  ecommerce: ["delivery/shopify-merchants"],
  "furniture-delivery": ["delivery/furniture"],
  "furniture-appliance": ["delivery/furniture"],
  appliances: ["delivery/furniture"],
};

/** Legacy furniture slugs (2025 /industries/*, /campaigns/*, /solutions/*) → the furniture hub. */
const FURNITURE_LEGACY_SLUGS = new Set([
  "furniture",
  "furniture-delivery",
  "furniture-appliance-delivery",
  "furniture-and-appliance-delivery",
  "appliance-delivery",
]);
const LEGACY_FURNITURE_FAMILIES = new Set(["industry", "industries", "campaigns", "solutions"]);
const furnitureHub = (slug: string | undefined): string[] =>
  slug && FURNITURE_LEGACY_SLUGS.has(slug) ? ["delivery/furniture"] : [];
const DELIVERY_AREA_ALIAS: Record<string, string> = {
  toronto: "downtown-toronto",
  oshawa: "oshawa-whitby",
  whitby: "oshawa-whitby",
  pickering: "pickering-ajax",
  ajax: "pickering-ajax",
  "richmond-hill": "richmond-hill",
};

function deliveryCandidates(p: string[]): string[] {
  const vertical = p[1] ?? "";
  const area = p[2] ? (DELIVERY_AREA_ALIAS[p[2]] ?? p[2]) : "";
  const verticalHubs = DELIVERY_VERTICAL_ALIAS[vertical] ?? [`delivery/${vertical}`];
  const out: string[] = [];
  for (const hub of verticalHubs) {
    if (area && hub.startsWith("delivery/")) out.push(`${hub}/${area}`);
  }
  if (area) out.push(`delivery/${vertical}/${area}`);
  out.push(...verticalHubs, "delivery");
  return out;
}

/** Families whose valid URLs are exactly the indexable manifest (+ fallbacks when not). */
const MANAGED_FAMILIES: Record<string, (parts: string[]) => string[]> = {
  delivery: deliveryCandidates,
  industry: (p) => [...furnitureHub(p[1]), `campaigns/${p[1] ?? ""}`, "delivery"],
  // The /campaigns hub was a 67-word link list (thin) → consolidated into /solutions.
  campaigns: (p) => [
    ...furnitureHub(p[1]),
    ...(p[1] ? [`industry/${p[1]}`] : []),
    ...(p[1] === "recurring-delivery" ? ["platform"] : []),
    "delivery",
  ],
  "service-areas": (p) => {
    const area = POLICY_CITY_TO_AREA[p[1] ?? ""];
    return [...(area && area !== p[1] ? [`service-areas/${area}`] : []), "service-areas"];
  },
  // FR calculator is an untranslated noindex shell → the EN calculator (same path, EN fallback).
  "delivery-cost-calculator": () => [],
  faq: () => ["faq"],
  guides: () => ["guides"],
  compare: () => ["compare"],
  "success-stories": () => ["delivery"],
  "integrations-education": () => ["integrations"],
  capabilities: () => ["platform"],
  "onboarding-education": () => ["guides"],
  solutions: (p) => [...furnitureHub(p[1]), "delivery"],
  developers: (p) => (p[1] === "docs" ? ["developers/docs", "developers"] : ["developers"]),
  "sedan-delivery": () => ["vehicles"],
  "cargo-van-delivery": () => ["vehicles"],
  "trade-van-delivery": () => ["vehicles"],
  "pickup-truck-delivery": () => ["vehicles"],
  "box-truck-delivery": () => ["vehicles"],
};

/** Families where only the hub (single segment) is managed; deeper paths are left alone. */
const HUB_ONLY_SINGLE = new Set(["developers"]);

const ROOT_FILE_MOVES: Record<string, string> = {
  "/openapi.json": "/en/developers",
};

/** Crawler artefacts from the 2026 /ca/ site (e.g. /ca/en/support-Support-0). */
const JUNK_PATTERNS: RegExp[] = [
  /-[A-Z][A-Za-z]*-\d+$/, // support-Support-0, pricing-Tarification-3
  /^(guidesGuides|industryIndustries|integrationsIntegrations)$/,
  /^\$$/,
];

type RegistryRule = { re: RegExp; keys: string[]; destination: string };

function compileRegistry(): RegistryRule[] {
  return WEBSITE_REDIRECTS.map(({ source, destination }) => {
    const keys: string[] = [];
    const pattern = source
      .split("/")
      .map((seg) => {
        const star = seg.match(/^:([a-zA-Z]+)\*$/);
        if (star) {
          keys.push(star[1]);
          return "(.*)";
        }
        const named = seg.match(/^:([a-zA-Z]+)$/);
        if (named) {
          keys.push(named[1]);
          return "([^/]+)";
        }
        return seg.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      })
      .join("/");
    return { re: new RegExp(`^${pattern}$`), keys, destination };
  });
}

const REGISTRY = compileRegistry();

function applyRegistry(path: string): { path: string; query: string; hash: string } | null {
  for (const rule of REGISTRY) {
    const m = path.match(rule.re);
    if (!m) continue;
    let dest = rule.destination;
    rule.keys.forEach((key, i) => {
      dest = dest.replace(new RegExp(`:${key}\\*?`, "g"), m[i + 1] ?? "");
    });
    const hashIdx = dest.indexOf("#");
    const hash = hashIdx >= 0 ? dest.slice(hashIdx) : "";
    if (hashIdx >= 0) dest = dest.slice(0, hashIdx);
    const qIdx = dest.indexOf("?");
    const query = qIdx >= 0 ? dest.slice(qIdx + 1) : "";
    if (qIdx >= 0) dest = dest.slice(0, qIdx);
    return { path: dest.replace(/\/+$/, "") || "/", query, hash };
  }
  return null;
}

/** Root (non-locale) paths that are real files/routes and must never get a locale prefix. */
const ROOT_PASSTHROUGH = new Set([
  "api",
  "_next",
  "_vercel",
  "monitoring",
  "sitemap",
  "sitemap.xml",
  "robots.txt",
  "llms.txt",
  "ravi",
  "proof-of-resolution",
  "brand",
  "icons",
  "images",
  "lottie",
  "favicon.ico",
  "icon.png",
  "icon.svg",
  "apple-icon",
  "opengraph-image",
  "__not-found__",
  "page-not-found",
]);

export type UrlPolicyResult =
  | { action: "redirect"; location: string; reason: string }
  | { action: "gone"; reason: string }
  | { action: "notfound"; reason: string }
  | { action: "pass" };

function managedFallback(locale: PolicyLocale, rest: string): string | null {
  const parts = rest.split("/").filter(Boolean);
  if (!parts.length) return null;
  const full = `/${locale}/${rest}`;
  const [first] = parts;

  // City × segment pages (app/[locale]/[city]/[industrySlug]) and bare legacy city URLs.
  const area = POLICY_CITY_TO_AREA[first];
  if (area && !LOCALE_APP_SECTIONS.has(first)) {
    if (parts.length === 2 && isIndexablePath(full)) return null;
    const seg = parts[1] ?? "";
    const candidates = [
      ...furnitureHub(seg),
      `service-areas/${area}`,
      ...(CITY_SEGMENT_HUB[seg] ?? []),
      "service-areas",
    ];
    return pickWithEnglishFallback(locale, rest, candidates);
  }

  const family = MANAGED_FAMILIES[first];
  if (!family) return null;
  if (HUB_ONLY_SINGLE.has(first) && parts.length === 1) return null;
  if (first === "developers" && parts[1] !== "docs") return null;
  if (isIndexablePath(full)) return null;
  // Legacy furniture slugs go straight to the furniture hub; FR has no hub yet, so the EN page
  // beats the generic FR /solutions page (single hop either way).
  if (furnitureHub(parts[1]).length && LEGACY_FURNITURE_FAMILIES.has(first)) {
    return (
      pickIndexable(locale, ["delivery/furniture"]) ??
      pickWithEnglishFallback("en", "", ["delivery/furniture"])
    );
  }
  return pickWithEnglishFallback(locale, rest, family(parts));
}

/**
 * Same-locale parent first; for FR URLs whose family only exists in English (e.g. the
 * /delivery matrix), the English page beats the FR home page as the closest equivalent.
 */
function pickWithEnglishFallback(locale: PolicyLocale, rest: string, candidates: string[]): string {
  const same = pickIndexable(locale, candidates);
  if (same) return same;
  if (locale !== "en") {
    if (isIndexablePath(`/en/${rest}`)) return `/en/${rest}`;
    const en = pickIndexable("en", candidates);
    if (en) return en;
  }
  return `/${locale}`;
}

function pickIndexable(locale: PolicyLocale, candidates: string[]): string | null {
  for (const c of candidates) {
    const p = `/${locale}/${c}`;
    if (isIndexablePath(p)) return p;
  }
  return null;
}

/** Query params worth keeping across a legacy redirect. */
const FUNCTIONAL_QUERY_KEYS = new Set([
  "t",
  "quote_id",
  "again",
  "pickup",
  "dropoff",
  "session_id",
]);

function carriedQuery(search: string): string {
  const params = new URLSearchParams(search);
  const kept = new URLSearchParams();
  for (const [k, v] of params) {
    // utm_* / gclid = attribution; intent/vehicle = functional quote-flow state (the target
    // pages are noindex or canonicalise to the clean URL). `from` is always dropped.
    // Signed / transactional state (track manage token, checkout + rebook handles) must survive
    // a locale or legacy redirect, otherwise emailed links silently lose their token.
    if (
      k.startsWith("utm_") ||
      k === "gclid" ||
      k === "intent" ||
      k === "vehicle" ||
      FUNCTIONAL_QUERY_KEYS.has(k)
    ) {
      kept.append(k, v);
    }
  }
  const s = kept.toString();
  return s ? `?${s}` : "";
}

/**
 * Decide what to do with a request path. `search` is the raw query string ("?a=b" or "").
 * Pure: same input → same output, independent of host (host canonicalisation is done in
 * middleware / Caddy).
 */
export function resolveUrlPolicy(pathname: string, search = ""): UrlPolicyResult {
  let path = pathname;
  const reasons: string[] = [];

  // 1. normalise
  const normalised =
    path
      .replace(/\/{2,}/g, "/")
      .replace(/\/index\.html?$/i, "")
      .replace(/\/+$/, "") || "/";
  if (normalised !== path) reasons.push("normalise");
  path = normalised;
  // "/index.html", "//" → straight to the default-locale home (not "/" → 307 → "/en").
  if (path === "/" && reasons.length > 0) {
    return { action: "redirect", location: `/en${carriedQuery(search)}`, reason: "normalise" };
  }

  const firstSeg = path.split("/")[1] ?? "";
  if (ROOT_PASSTHROUGH.has(firstSeg) && reasons.length === 0) return { action: "pass" };

  // 2. legacy prefixes (loop: /ca/en/en/... etc.)
  for (let i = 0; i < 4; i++) {
    const before = path;
    path = path
      .replace(/^\/ca\/(en|en-ca)(?=\/|$)/, "/en")
      .replace(/^\/ca\/(fr-ca|fr)(?=\/|$)/, "/fr")
      .replace(/^\/ca(?=\/|$)/, "/en")
      .replace(/^\/(en-ca|en-us)(?=\/|$)/i, "/en")
      .replace(/^\/fr-ca(?=\/|$)/i, "/fr")
      .replace(/^\/(en|fr)\/(en|fr)(?=\/|$)/, "/$2");
    if (path === before) break;
    reasons.push("legacy-prefix");
  }

  // Root files the old site served that now live elsewhere (the API spec is on the API host;
  // the developer hub links it).
  const movedFile = ROOT_FILE_MOVES[path];
  if (movedFile) return { action: "redirect", location: movedFile, reason: "moved-file" };

  let [, locale, ...restParts] = path.split("/");
  if (!POLICY_LOCALES.includes(locale as PolicyLocale)) {
    if (path === "/" || ROOT_PASSTHROUGH.has(locale) || /\.[a-z0-9]+$/i.test(path)) {
      return reasons.length
        ? { action: "redirect", location: path + carriedQuery(search), reason: reasons.join("+") }
        : { action: "pass" };
    }
    // Locale-less legacy URL (2025–2026 sites) → English.
    path = `/en${path}`;
    reasons.push("no-locale");
    [, locale, ...restParts] = path.split("/");
  }
  const loc = locale as PolicyLocale;
  let rest = restParts.join("/");

  // 3. junk → 410
  const last = restParts[restParts.length - 1] ?? "";
  if (JUNK_PATTERNS.some((re) => re.test(last))) return { action: "gone", reason: "junk" };

  // 4. registry (renames / retired hubs) to a fixed point
  let query = "";
  let hash = "";
  for (let i = 0; i < 6; i++) {
    const hit = applyRegistry(`/${loc}${rest ? `/${rest}` : ""}`);
    if (!hit) break;
    const nextRest = hit.path.split("/").slice(2).join("/");
    query = hit.query;
    hash = hit.hash;
    if (nextRest === rest) break;
    rest = nextRest;
    reasons.push("registry");
  }
  path = `/${loc}${rest ? `/${rest}` : ""}`;

  // 5. managed programmatic families → nearest indexable parent
  if (!query) {
    const fallback = managedFallback(loc, rest);
    if (fallback && fallback !== path) {
      path = fallback;
      hash = "";
      reasons.push("not-indexable");
    }
  }

  // 6. deep paths outside every known section would hit the [city]/[segment] catch-all and
  //    render a soft 404 — answer with a real 404 instead (no redirect to a dead end).
  const top = path.split("/")[2] ?? "";
  const depth = path.split("/").length - 2;
  if (depth >= 2 && !LOCALE_APP_SECTIONS.has(top) && !POLICY_CITY_TO_AREA[top]) {
    return { action: "notfound", reason: "unknown-section" };
  }

  if (!reasons.length) return { action: "pass" };
  const qs = query ? `?${query}` : carriedQuery(search);
  return { action: "redirect", location: `${path}${qs}${hash}`, reason: reasons.join("+") };
}
