import { publicEnv } from "@/lib/env";

/** Public phone for schema.org and GBP NAP consistency. */
export const PUBLIC_CONTACT_PHONE_E164 = "+16476197951";

export function isGoogleBusinessProfileConfigured(): boolean {
  return publicEnv.googleBusinessProfileUrl.length > 0;
}

export function isGoogleBusinessReviewConfigured(): boolean {
  return (
    publicEnv.googleBusinessReviewUrl.length > 0 || isGoogleBusinessProfileConfigured()
  );
}

/** Maps / profile URL for “Find us on Google” and schema.org sameAs. */
export function getGoogleBusinessProfileUrl(): string {
  return publicEnv.googleBusinessProfileUrl;
}

/** Direct “Write a review” link when configured; otherwise profile URL. */
export function getGoogleBusinessReviewUrl(): string {
  if (publicEnv.googleBusinessReviewUrl.length > 0) {
    return publicEnv.googleBusinessReviewUrl;
  }
  return publicEnv.googleBusinessProfileUrl;
}

/** Social + GBP links for LocalBusiness sameAs (NAP alignment with Google). */
export function buildGoogleSameAsLinks(): string[] {
  const links = [
    publicEnv.socialLinkedIn,
    publicEnv.socialFacebook,
    publicEnv.socialInstagram,
    publicEnv.socialYouTube,
    publicEnv.googleBusinessProfileUrl,
  ].map((url) => url.trim()).filter(Boolean);
  return [...new Set(links)];
}
