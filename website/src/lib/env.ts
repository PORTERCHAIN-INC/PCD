/**
 * Typed public environment variables for the website.
 * Server-only secrets belong in the API — never add them here.
 */
export const publicEnv = {
  googleMapsApiKey: (process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ?? "").trim(),
  siteUrl: (process.env.NEXT_PUBLIC_SITE_URL ?? "https://porterchain.com").replace(
    /\/$/,
    ""
  ),
  merchantPortalUrl: (
    process.env.NEXT_PUBLIC_MERCHANT_PORTAL_URL ??
    (process.env.NODE_ENV === "development"
      ? "http://localhost:3001"
      : "https://portal.porterchain.com")
  ).replace(/\/$/, ""),
  driverPortalUrl: (
    process.env.NEXT_PUBLIC_DRIVER_PORTAL_URL ??
    (process.env.NODE_ENV === "development"
      ? "http://localhost:3003"
      : "https://portal.porterchain.com")
  ).replace(/\/$/, ""),
  porterchainApiUrl: (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
    /\/$/,
    ""
  ),
  clerkPublishableKey: (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim(),
  supabaseUrl: (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").trim(),
  supabaseAnonKey: (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "").trim(),
  bookingOtpSkipVerify: process.env.NEXT_PUBLIC_BOOKING_OTP_SKIP_VERIFY === "true",
  zohoSalesIqEnabled: process.env.NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED === "true",
  zohoSalesIqWidgetCode: (process.env.NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE ?? "").trim(),
  socialLinkedIn:
    (process.env.NEXT_PUBLIC_SOCIAL_LINKEDIN ?? "https://www.linkedin.com/company/porterchain").trim(),
  socialInstagram:
    (process.env.NEXT_PUBLIC_SOCIAL_INSTAGRAM ?? "https://www.instagram.com/porterchain/").trim(),
  socialFacebook:
    (
      process.env.NEXT_PUBLIC_SOCIAL_FACEBOOK ??
      "https://www.facebook.com/profile.php?id=61568324733884"
    ).trim(),
  socialYouTube: (process.env.NEXT_PUBLIC_SOCIAL_YOUTUBE ?? "https://www.youtube.com/@porterchain").trim(),
  socialWhatsApp: (process.env.NEXT_PUBLIC_SOCIAL_WHATSAPP ?? "https://wa.me/16476197951").trim(),
} as const;

export function isGoogleMapsConfigured(): boolean {
  return publicEnv.googleMapsApiKey.length > 0;
}

export function isPorterchainApiConfigured(): boolean {
  return publicEnv.porterchainApiUrl.length > 0;
}

export function isClerkConfigured(): boolean {
  return publicEnv.clerkPublishableKey.length > 0;
}

export function isSupabaseConfigured(): boolean {
  return publicEnv.supabaseUrl.length > 0 && publicEnv.supabaseAnonKey.length > 0;
}

export function isZohoSalesIqConfigured(): boolean {
  return publicEnv.zohoSalesIqEnabled && publicEnv.zohoSalesIqWidgetCode.length > 0;
}
