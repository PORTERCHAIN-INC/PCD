/**
 * Public marketing integration IDs — all optional / dark until set.
 * When GTM is set, browser pixels should be configured in GTM (not double-fired here).
 */

function trimEnv(value: string | undefined): string {
  return (value ?? "").trim();
}

export const marketingPublicEnv = {
  gtmId: trimEnv(process.env.NEXT_PUBLIC_GTM_ID),
  gaMeasurementId: trimEnv(process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID),
  googleAdsId: trimEnv(process.env.NEXT_PUBLIC_GOOGLE_ADS_ID),
  googleAdsQuoteLabel: trimEnv(process.env.NEXT_PUBLIC_GOOGLE_ADS_QUOTE_LABEL),
  microsoftUetId: trimEnv(process.env.NEXT_PUBLIC_MICROSOFT_UET_ID),
  linkedInPartnerId: trimEnv(process.env.NEXT_PUBLIC_LINKEDIN_PARTNER_ID),
  metaPixelId: trimEnv(process.env.NEXT_PUBLIC_META_PIXEL_ID),
  twitterPixelId: trimEnv(process.env.NEXT_PUBLIC_TWITTER_PIXEL_ID),
  clarityId: trimEnv(process.env.NEXT_PUBLIC_CLARITY_ID),
  hotjarId: trimEnv(process.env.NEXT_PUBLIC_HOTJAR_ID),
  bingSiteVerification: trimEnv(process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION),
  yandexSiteVerification: trimEnv(process.env.NEXT_PUBLIC_YANDEX_SITE_VERIFICATION),
  /** Prefer Clarity when both experience tools are configured. */
  get experienceTool(): "clarity" | "hotjar" | null {
    if (this.clarityId) return "clarity";
    if (this.hotjarId) return "hotjar";
    return null;
  },
  /** When GTM is present, skip direct marketing pixel loaders. */
  get useGtmForMarketing(): boolean {
    return this.gtmId.length > 0;
  },
} as const;

export type HubAttributionFrom = "chooser" | "merchants-hub" | "drivers-hub";

export const HUB_FROM = {
  chooser: "chooser",
  merchants: "merchants-hub",
  drivers: "drivers-hub",
} as const satisfies Record<string, HubAttributionFrom>;
