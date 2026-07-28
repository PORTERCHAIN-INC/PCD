/**
 * Typed public environment variables for the website.
 * Server-only secrets belong in the API — never add them here.
 *
 * Next.js inlines missing NEXT_PUBLIC_* as "" at build time, so `??` defaults
 * never apply. Use empty-string-aware helpers instead.
 */
import { getPorterchainApiBase } from "@/lib/api-base";

function envText(value: string | undefined): string {
  return (value ?? "").trim();
}

function envOr(value: string | undefined, fallback: string): string {
  const trimmed = envText(value);
  return trimmed.length > 0 ? trimmed : fallback;
}

const isDev = process.env.NODE_ENV === "development";

export const publicEnv = {
  googleMapsApiKey: envText(process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY),
  siteUrl: envOr(process.env.NEXT_PUBLIC_SITE_URL, "https://porterchain.com").replace(/\/$/, ""),
  merchantPortalUrl: envOr(
    process.env.NEXT_PUBLIC_MERCHANT_PORTAL_URL,
    isDev ? "http://localhost:3001" : "https://merchant.porterchain.com"
  ).replace(/\/$/, ""),
  adminPortalUrl: envOr(
    process.env.NEXT_PUBLIC_ADMIN_PORTAL_URL,
    isDev ? "http://localhost:3002" : "https://admin.porterchain.com"
  ).replace(/\/$/, ""),
  customerPortalUrl: envOr(
    process.env.NEXT_PUBLIC_CUSTOMER_PORTAL_URL,
    isDev ? "http://localhost:3004" : "https://customer.porterchain.com"
  ).replace(/\/$/, ""),
  driverPortalUrl: envOr(
    process.env.NEXT_PUBLIC_DRIVER_PORTAL_URL,
    isDev ? "http://localhost:3003" : "https://driver.porterchain.com"
  ).replace(/\/$/, ""),
  porterchainApiUrl: envText(process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL).replace(/\/$/, ""),
  clerkPublishableKey: envText(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY),
  contactEmail: envOr(process.env.NEXT_PUBLIC_CONTACT_EMAIL, "enterprise@porterchain.com"),
  zohoSalesIqEnabled: process.env.NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED === "true",
  zohoSalesIqWidgetCode: envText(process.env.NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE),
  gaMeasurementId: envText(process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID),
  googleSiteVerification: envText(process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION),
  /** Google Business Profile (Maps) public URL — set after claiming GBP. */
  googleBusinessProfileUrl: envText(process.env.NEXT_PUBLIC_GOOGLE_BUSINESS_PROFILE_URL),
  /** Optional direct “Write a review” URL from GBP dashboard. */
  googleBusinessReviewUrl: envText(process.env.NEXT_PUBLIC_GOOGLE_BUSINESS_REVIEW_URL),
  contactPhone: envOr(process.env.NEXT_PUBLIC_CONTACT_PHONE, "+16476197951"),
  socialLinkedIn: envOr(
    process.env.NEXT_PUBLIC_SOCIAL_LINKEDIN,
    "https://www.linkedin.com/company/porterchain"
  ),
  socialInstagram: envOr(
    process.env.NEXT_PUBLIC_SOCIAL_INSTAGRAM,
    "https://www.instagram.com/porterchain/"
  ),
  socialFacebook: envOr(
    process.env.NEXT_PUBLIC_SOCIAL_FACEBOOK,
    "https://www.facebook.com/profile.php?id=61568324733884"
  ),
  socialYouTube: envOr(
    process.env.NEXT_PUBLIC_SOCIAL_YOUTUBE,
    "https://www.youtube.com/@porterchain"
  ),
  socialWhatsApp: envOr(process.env.NEXT_PUBLIC_SOCIAL_WHATSAPP, "https://wa.me/16476197951"),
  driverAppIosUrl: envText(process.env.NEXT_PUBLIC_DRIVER_APP_IOS_URL),
  driverAppAndroidUrl: envText(process.env.NEXT_PUBLIC_DRIVER_APP_ANDROID_URL),
  allowStripeMock: process.env.NEXT_PUBLIC_ALLOW_STRIPE_MOCK === "true",
  gtmId: envText(process.env.NEXT_PUBLIC_GTM_ID),
  googleAdsId: envText(process.env.NEXT_PUBLIC_GOOGLE_ADS_ID),
  googleAdsQuoteLabel: envText(process.env.NEXT_PUBLIC_GOOGLE_ADS_QUOTE_LABEL),
  microsoftUetId: envText(process.env.NEXT_PUBLIC_MICROSOFT_UET_ID),
  linkedInPartnerId: envText(process.env.NEXT_PUBLIC_LINKEDIN_PARTNER_ID),
  metaPixelId: envText(process.env.NEXT_PUBLIC_META_PIXEL_ID),
  twitterPixelId: envText(process.env.NEXT_PUBLIC_TWITTER_PIXEL_ID),
  clarityId: envText(process.env.NEXT_PUBLIC_CLARITY_ID),
  hotjarId: envText(process.env.NEXT_PUBLIC_HOTJAR_ID),
  bingSiteVerification: envText(process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION),
  yandexSiteVerification: envText(process.env.NEXT_PUBLIC_YANDEX_SITE_VERIFICATION),
} as const;

export function isGoogleMapsConfigured(): boolean {
  return publicEnv.googleMapsApiKey.length > 0;
}

export function isPorterchainApiConfigured(): boolean {
  return Boolean(getPorterchainApiBase());
}

export function isClerkConfigured(): boolean {
  return publicEnv.clerkPublishableKey.length > 0;
}

export function isZohoSalesIqConfigured(): boolean {
  return publicEnv.zohoSalesIqEnabled && publicEnv.zohoSalesIqWidgetCode.length > 0;
}

export function isDriverAppConfigured(): boolean {
  return publicEnv.driverAppIosUrl.length > 0 || publicEnv.driverAppAndroidUrl.length > 0;
}
