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
