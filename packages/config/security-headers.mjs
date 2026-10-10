/**
 * Shared HTTP security headers + Content-Security-Policy builders (readiness audit #11).
 *
 * Strategy:
 * - ENFORCED baseline CSP everywhere: directives that cannot break Clerk/Stripe/Maps/analytics
 *   (no plugins, no <base> hijack, no framing by other sites).
 * - Website additionally ships a full allowlist policy as Content-Security-Policy-Report-Only
 *   (browser console reports violations, nothing is blocked). Promote it to enforced with
 *   WEBSITE_CSP_ENFORCE=true once production consoles are clean for a week.
 *   Next.js inline bootstrap scripts need 'unsafe-inline' unless a per-request nonce is used,
 *   which would disable static/PPR rendering (cacheComponents) — so we keep 'unsafe-inline'.
 */

/** @param {{ frameAncestors?: string }} [opts] */
export function baselineCsp(opts = {}) {
  const frameAncestors = opts.frameAncestors ?? "'none'";
  return ["base-uri 'self'", "object-src 'none'", `frame-ancestors ${frameAncestors}`].join("; ");
}

/** @param {{ frameAncestors?: string, frameDeny?: boolean }} [opts] */
export function baselineSecurityHeaders(opts = {}) {
  const headers = [
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Content-Security-Policy", value: baselineCsp(opts) },
  ];
  if (opts.frameDeny !== false && !opts.frameAncestors) {
    headers.push({ key: "X-Frame-Options", value: "DENY" });
  }
  return headers;
}

function originOf(url) {
  try {
    const u = new URL(url);
    return `${u.protocol}//${u.host}`;
  } catch {
    return "";
  }
}

const CLERK = [
  "https://clerk.porterchain.com",
  "https://clerk.admin.porterchain.com",
  "https://clerk.driver.porterchain.com",
  "https://accounts.porterchain.com",
  "https://*.clerk.accounts.dev",
  "https://*.clerk.com",
  "https://challenges.cloudflare.com",
];
const GOOGLE = [
  "https://www.googletagmanager.com",
  "https://*.google-analytics.com",
  "https://*.analytics.google.com",
  "https://www.googleadservices.com",
  "https://googleads.g.doubleclick.net",
  "https://*.doubleclick.net",
  "https://www.google.com",
  "https://maps.googleapis.com",
  "https://maps.gstatic.com",
];
const ADS = [
  "https://connect.facebook.net",
  "https://www.facebook.com",
  "https://snap.licdn.com",
  "https://px.ads.linkedin.com",
  "https://bat.bing.com",
  "https://static.ads-twitter.com",
  "https://analytics.twitter.com",
  "https://www.clarity.ms",
  "https://*.clarity.ms",
  "https://static.hotjar.com",
  "https://script.hotjar.com",
  "https://*.hotjar.com",
  "wss://*.hotjar.com",
];
const STRIPE = ["https://js.stripe.com", "https://api.stripe.com", "https://hooks.stripe.com"];
const SENTRY = [
  "https://*.ingest.sentry.io",
  "https://*.ingest.us.sentry.io",
  "https://*.ingest.de.sentry.io",
];

/**
 * Full website policy.
 * @param {{ apiUrl?: string, extraConnect?: string[], dev?: boolean }} [opts]
 */
export function websiteCsp(opts = {}) {
  const api = originOf(opts.apiUrl ?? "");
  const connect = [
    "'self'",
    api,
    "https://porterchain.com",
    "https://*.porterchain.com",
    ...CLERK,
    ...GOOGLE,
    ...ADS,
    ...STRIPE,
    ...SENTRY,
    ...(opts.extraConnect ?? []),
  ].filter(Boolean);
  if (opts.dev) connect.push("ws:", "http://localhost:*");
  const scriptSrc = [
    "'self'",
    "'unsafe-inline'",
    ...CLERK,
    ...GOOGLE,
    ...ADS,
    "https://js.stripe.com",
  ];
  if (opts.dev) scriptSrc.push("'unsafe-eval'");
  return [
    "default-src 'self'",
    `script-src ${scriptSrc.join(" ")}`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "img-src 'self' data: blob: https:" + (opts.dev ? " http://localhost:*" : ""),
    "font-src 'self' data: https://fonts.gstatic.com",
    `connect-src ${[...new Set(connect)].join(" ")}`,
    `frame-src 'self' ${[...CLERK, "https://js.stripe.com", "https://hooks.stripe.com", "https://www.googletagmanager.com", "https://www.youtube.com", "https://www.youtube-nocookie.com", "https://www.google.com"].join(" ")}`,
    "worker-src 'self' blob:",
    "media-src 'self' https: blob:",
    "manifest-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self' https://*.clerk.accounts.dev https://clerk.porterchain.com https://accounts.porterchain.com",
  ].join("; ");
}

const SHOPIFY = ["https://cdn.shopify.com", "https://admin.shopify.com", "https://*.myshopify.com"];
const MAPS = [
  "https://maps.googleapis.com",
  "https://maps.gstatic.com",
  "https://*.tile.openstreetmap.org",
  "https://tile.openstreetmap.org",
  "https://tiles.openfreemap.org",
  "https://*.basemaps.cartocdn.com",
  "https://demotiles.maplibre.org",
];
const FIREBASE = [
  "https://www.gstatic.com",
  "https://*.googleapis.com",
  "https://*.firebaseio.com",
  "https://fcmregistrations.googleapis.com",
];

/**
 * Enforced per-portal policy with script rules (security audit 2026-10-10).
 * Scripts only from self + the vendors each app really loads; no plugins, no framing,
 * no <base> hijack, forms only to self/Clerk. 'unsafe-inline' stays for Next.js
 * bootstrap scripts (no nonce: static rendering), 'unsafe-eval' only in dev.
 * @param {{ app: "admin"|"merchant"|"customer"|"driver", apiUrl?: string, mapTileUrl?: string,
 *           valhallaUrl?: string, frameAncestors?: string, dev?: boolean }} opts
 */
export function portalCsp(opts) {
  const app = opts.app;
  const clerk = app === "admin" ? [] : CLERK;
  const stripe = app === "customer" || app === "merchant" ? STRIPE : [];
  const shopify = app === "merchant" ? SHOPIFY : [];
  const firebase = app === "driver" || app === "admin" ? FIREBASE : [];
  const extraOrigins = [opts.apiUrl, opts.mapTileUrl, opts.valhallaUrl]
    .map((u) => originOf(u ?? ""))
    .filter(Boolean);
  const scriptSrc = [
    "'self'",
    "'unsafe-inline'",
    ...clerk,
    ...stripe.slice(0, 1),
    ...shopify.slice(0, 1),
    "https://maps.googleapis.com",
    "https://www.googletagmanager.com",
    ...firebase.slice(0, 1),
  ];
  if (opts.dev) scriptSrc.push("'unsafe-eval'");
  const connect = [
    "'self'",
    "https://porterchain.com",
    "https://*.porterchain.com",
    "wss://*.porterchain.com",
    ...extraOrigins,
    ...clerk,
    ...stripe,
    ...shopify,
    ...MAPS,
    ...firebase,
    ...SENTRY,
    "https://*.google-analytics.com",
    "https://*.analytics.google.com",
  ];
  if (opts.dev) connect.push("ws:", "http://localhost:*", "http://127.0.0.1:*");
  return [
    "default-src 'self'",
    `script-src ${[...new Set(scriptSrc)].join(" ")}`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "img-src 'self' data: blob: https:" + (opts.dev ? " http://localhost:*" : ""),
    "font-src 'self' data: https://fonts.gstatic.com",
    `connect-src ${[...new Set(connect)].join(" ")}`,
    `frame-src 'self' ${[...clerk, ...stripe, ...shopify].join(" ")}`.trim(),
    "worker-src 'self' blob:",
    "child-src 'self' blob:",
    "media-src 'self' blob: https:",
    "manifest-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    `frame-ancestors ${opts.frameAncestors ?? "'none'"}`,
    `form-action 'self' ${clerk.join(" ")}`.trim(),
    ...(opts.dev ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");
}

/** Headers for a portal app (enforced portalCsp). Reads public env at build time. */
export function portalSecurityHeaders(app, opts = {}) {
  const env = process.env;
  const csp = portalCsp({
    app,
    apiUrl: env.NEXT_PUBLIC_PORTERCHAIN_API_URL,
    mapTileUrl: env.NEXT_PUBLIC_MAP_TILE_URL,
    valhallaUrl: env.NEXT_PUBLIC_VALHALLA_URL,
    dev: env.NODE_ENV !== "production",
    frameAncestors: opts.frameAncestors,
  });
  const headers = [
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Content-Security-Policy", value: csp },
    {
      key: "Cross-Origin-Opener-Policy",
      value: opts.frameAncestors ? "unsafe-none" : "same-origin-allow-popups",
    },
  ];
  if (!opts.frameAncestors) headers.push({ key: "X-Frame-Options", value: "DENY" });
  return headers;
}
