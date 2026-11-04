/**
 * Shared HTTP security headers + Content-Security-Policy builders (readiness audit #11).
 *
 * Strategy:
 * - ENFORCED baseline CSP everywhere: directives that cannot break Keycloak/Stripe/Maps/analytics
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

/** The websocket origin for an API origin (http -> ws, https -> wss), for live updates. */
function wsOriginOf(origin) {
  if (origin.startsWith("https://")) return `wss://${origin.slice(8)}`;
  if (origin.startsWith("http://")) return `ws://${origin.slice(7)}`;
  return "";
}

function originOf(url) {
  try {
    const u = new URL(url);
    return `${u.protocol}//${u.host}`;
  } catch {
    return "";
  }
}

/**
 * Keycloak (self-hosted IdP). Sign-in is a top-level redirect, so only form-action needs it
 * (Keycloak login/logout forms post back to the IdP host).
 */
const KEYCLOAK_DEFAULT = ["https://auth.porterchain.com", "http://localhost:8180"];
/** Plus the public Keycloak origin of this build (e.g. LAN stack http://192.168.x.x:18280). */
function keycloakOrigins() {
  const extra = originOf(process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? "");
  return [...new Set([...KEYCLOAK_DEFAULT, ...(extra ? [extra] : [])])];
}
const GOOGLE = [
  "https://www.googletagmanager.com",
  "https://*.google-analytics.com",
  "https://*.analytics.google.com",
  "https://www.googleadservices.com",
  "https://googleads.g.doubleclick.net",
  "https://*.doubleclick.net",
  "https://www.google.com",
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
/** GlitchTip (self-hosted error tracking): the origin of the public DSN, when set. */
function errorTrackingOrigins(dsn) {
  const origin = originOf(dsn ?? "");
  return origin ? [origin] : [];
}

/**
 * Full website policy.
 * @param {{ apiUrl?: string, errorsDsn?: string, extraConnect?: string[], dev?: boolean }} [opts]
 */
export function websiteCsp(opts = {}) {
  const api = originOf(opts.apiUrl ?? "");
  const connect = [
    "'self'",
    api,
    "https://porterchain.com",
    "https://*.porterchain.com",
    ...GOOGLE,
    ...ADS,
    ...STRIPE,
    ...errorTrackingOrigins(opts.errorsDsn),
    ...(opts.extraConnect ?? []),
  ].filter(Boolean);
  if (opts.dev) connect.push("ws:", "http://localhost:*");
  const scriptSrc = ["'self'", "'unsafe-inline'", ...GOOGLE, ...ADS, "https://js.stripe.com"];
  if (opts.dev) scriptSrc.push("'unsafe-eval'");
  return [
    "default-src 'self'",
    `script-src ${scriptSrc.join(" ")}`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "img-src 'self' data: blob: https:" + (opts.dev ? " http://localhost:*" : ""),
    "font-src 'self' data: https://fonts.gstatic.com",
    `connect-src ${[...new Set(connect)].join(" ")}`,
    `frame-src 'self' ${["https://js.stripe.com", "https://hooks.stripe.com", "https://www.googletagmanager.com", "https://www.youtube.com", "https://www.youtube-nocookie.com", "https://www.google.com"].join(" ")}`,
    "worker-src 'self' blob:",
    "media-src 'self' https: blob:",
    "manifest-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    `form-action 'self' ${keycloakOrigins().join(" ")}`,
  ].join("; ");
}

const SHOPIFY = ["https://cdn.shopify.com", "https://admin.shopify.com", "https://*.myshopify.com"];
// Self-hosted Protomaps PMTiles + fonts/sprites (MapLibre). No Google Maps hosts.
const MAPS = [
  "https://tiles.porterchain.com",
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
 * no <base> hijack, forms only to self/Keycloak. 'unsafe-inline' stays for Next.js
 * bootstrap scripts (no nonce: static rendering), 'unsafe-eval' only in dev.
 * @param {{ app: "admin"|"merchant"|"customer"|"driver", apiUrl?: string, mapTileUrl?: string,
 *           valhallaUrl?: string, errorsDsn?: string, frameAncestors?: string, dev?: boolean }} opts
 */
export function portalCsp(opts) {
  const app = opts.app;
  const stripe = app === "customer" || app === "merchant" ? STRIPE : [];
  const shopify = app === "merchant" ? SHOPIFY : [];
  const firebase = app === "driver" || app === "admin" ? FIREBASE : [];
  const extraOrigins = [opts.apiUrl, opts.mapTileUrl, opts.valhallaUrl]
    .map((u) => originOf(u ?? ""))
    .filter(Boolean);
  const scriptSrc = [
    "'self'",
    "'unsafe-inline'",
    ...stripe.slice(0, 1),
    ...shopify.slice(0, 1),
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
    wsOriginOf(originOf(opts.apiUrl ?? "")),
    ...stripe,
    ...shopify,
    ...MAPS,
    ...firebase,
    ...errorTrackingOrigins(opts.errorsDsn),
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
    `connect-src ${[...new Set(connect.filter(Boolean))].join(" ")}`,
    `frame-src 'self' ${[...stripe, ...shopify].join(" ")}`.trim(),
    "worker-src 'self' blob:",
    "child-src 'self' blob:",
    "media-src 'self' blob: https:",
    "manifest-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    `frame-ancestors ${opts.frameAncestors ?? "'none'"}`,
    `form-action 'self' ${keycloakOrigins().join(" ")}`.trim(),
    // Plain-http LAN/local stacks (NEXT_PUBLIC_SITE_URL=http://…) must not upgrade: no TLS there.
    ...(opts.dev || opts.plainHttp ? [] : ["upgrade-insecure-requests"]),
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
    errorsDsn: env.NEXT_PUBLIC_GLITCHTIP_DSN,
    dev: env.NODE_ENV !== "production",
    plainHttp: String(env.NEXT_PUBLIC_SITE_URL || "").startsWith("http://"),
    frameAncestors: opts.frameAncestors,
  });
  const plainHttp = String(env.NEXT_PUBLIC_SITE_URL || "").startsWith("http://");
  const headers = [
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Content-Security-Policy", value: csp },
  ];
  // COOP is ignored (with a console warning) on untrustworthy plain-http origins; send it only on HTTPS.
  if (!plainHttp) {
    headers.push({
      key: "Cross-Origin-Opener-Policy",
      value: opts.frameAncestors ? "unsafe-none" : "same-origin-allow-popups",
    });
  }
  if (!opts.frameAncestors) headers.push({ key: "X-Frame-Options", value: "DENY" });
  return headers;
}
