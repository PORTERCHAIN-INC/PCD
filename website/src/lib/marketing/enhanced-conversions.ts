/** SHA-256 hex for Google Ads Enhanced Conversions (email). Browser Web Crypto. */
export async function hashEmailForEnhancedConversions(email: string): Promise<string | null> {
  const normalized = email.trim().toLowerCase();
  if (!normalized || !normalized.includes("@")) return null;
  if (typeof window === "undefined" || !window.crypto?.subtle) return null;
  const data = new TextEncoder().encode(normalized);
  const digest = await window.crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Fire Google Ads conversion when IDs + marketing consent are present. */
export function fireGoogleAdsQuoteConversion(hashedEmail?: string | null): void {
  const adsId = (process.env.NEXT_PUBLIC_GOOGLE_ADS_ID ?? "").trim();
  const label = (process.env.NEXT_PUBLIC_GOOGLE_ADS_QUOTE_LABEL ?? "").trim();
  if (!adsId || !label || typeof window === "undefined") return;
  const gtag = (window as Window & { gtag?: (...args: unknown[]) => void }).gtag;
  if (!gtag) return;
  gtag("event", "conversion", {
    send_to: `${adsId}/${label}`,
    ...(hashedEmail
      ? {
          user_data: {
            sha256_email_address: hashedEmail,
          },
        }
      : {}),
  });
}
