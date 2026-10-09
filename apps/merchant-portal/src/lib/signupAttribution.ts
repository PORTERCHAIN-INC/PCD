/**
 * First-touch marketing attribution carried from the website into merchant signup.
 * The website appends utm_* / from / pc_vid to the portal URL (subdomains do not
 * share storage); we keep the first values for this browser session and send them
 * with the onboarding "business type" step.
 */

export const SIGNUP_ATTRIBUTION_KEY = "pc_signup_attribution";

const KEYS = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_term",
  "utm_content",
  "from",
  "pc_vid",
] as const;

export type SignupAttribution = Partial<
  Record<(typeof KEYS)[number] | "landing_page" | "referrer", string>
>;

export function parseSignupAttribution(
  search: string,
  extras: { landingPage?: string; referrer?: string } = {}
): SignupAttribution {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const out: SignupAttribution = {};
  for (const key of KEYS) {
    const value = params.get(key)?.trim();
    if (value) out[key] = value.slice(0, 120);
  }
  if (!Object.keys(out).length) return out;
  if (extras.landingPage) out.landing_page = extras.landingPage.slice(0, 500);
  if (extras.referrer) out.referrer = extras.referrer.slice(0, 500);
  return out;
}

/** Store first-touch attribution for this session (never overwritten). */
export function rememberSignupAttribution(): void {
  if (typeof window === "undefined") return;
  try {
    if (window.sessionStorage.getItem(SIGNUP_ATTRIBUTION_KEY)) return;
    const found = parseSignupAttribution(window.location.search, {
      landingPage: window.location.href,
      referrer: document.referrer || undefined,
    });
    if (Object.keys(found).length) {
      window.sessionStorage.setItem(SIGNUP_ATTRIBUTION_KEY, JSON.stringify(found));
    }
  } catch {
    /* private mode */
  }
}

export function readSignupAttribution(): SignupAttribution | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const raw = window.sessionStorage.getItem(SIGNUP_ATTRIBUTION_KEY);
    return raw ? (JSON.parse(raw) as SignupAttribution) : undefined;
  } catch {
    return undefined;
  }
}
