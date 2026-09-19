/**
 * Marketing consent + Consent Mode v2 helpers.
 * Defaults denied until the user grants categories via CMP.
 */

export type ConsentCategory = "necessary" | "analytics" | "marketing" | "experience";

export type ConsentState = {
  necessary: true;
  analytics: boolean;
  marketing: boolean;
  experience: boolean;
  updatedAt: string;
};

export const CONSENT_STORAGE_KEY = "pc_cookie_consent_v1";

export const DEFAULT_CONSENT: ConsentState = {
  necessary: true,
  analytics: false,
  marketing: false,
  experience: false,
  updatedAt: "",
};

export function readStoredConsent(): ConsentState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(CONSENT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ConsentState>;
    return {
      necessary: true,
      analytics: Boolean(parsed.analytics),
      marketing: Boolean(parsed.marketing),
      experience: Boolean(parsed.experience),
      updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : "",
    };
  } catch {
    return null;
  }
}

export function writeStoredConsent(
  state: Omit<ConsentState, "necessary" | "updatedAt">
): ConsentState {
  const next: ConsentState = {
    necessary: true,
    analytics: state.analytics,
    marketing: state.marketing,
    experience: state.experience,
    updatedAt: new Date().toISOString(),
  };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(next));
  }
  return next;
}

/** Push Google Consent Mode v2 defaults / updates to dataLayer. */
export function applyGoogleConsentMode(consent: ConsentState): void {
  if (typeof window === "undefined") return;
  const w = window as Window & {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  };
  w.dataLayer = w.dataLayer || [];
  const gtag =
    w.gtag ??
    function gtag(...args: unknown[]) {
      w.dataLayer?.push(args);
    };
  w.gtag = gtag;

  const payload = {
    ad_storage: consent.marketing ? "granted" : "denied",
    ad_user_data: consent.marketing ? "granted" : "denied",
    ad_personalization: consent.marketing ? "granted" : "denied",
    analytics_storage: consent.analytics ? "granted" : "denied",
    functionality_storage: "granted",
    security_storage: "granted",
    wait_for_update: 500,
  } as const;

  gtag("consent", "update", payload);
}

/** Call once before any gtag config — default denied. */
export function ensureGoogleConsentDefaults(): void {
  if (typeof window === "undefined") return;
  const w = window as Window & { dataLayer?: unknown[]; __pcConsentDefaults?: boolean };
  if (w.__pcConsentDefaults) return;
  w.__pcConsentDefaults = true;
  w.dataLayer = w.dataLayer || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function gtag(...args: any[]) {
    w.dataLayer?.push(args);
  }
  (window as unknown as { gtag: typeof gtag }).gtag = gtag;
  gtag("consent", "default", {
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: "denied",
    functionality_storage: "granted",
    security_storage: "granted",
    wait_for_update: 500,
  });
  const stored = readStoredConsent();
  if (stored) applyGoogleConsentMode(stored);
}
