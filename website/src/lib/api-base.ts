/**
 * API base URL for browser and server fetches.
 * Production website uses same-origin (Caddy proxies /v1/* → API) to avoid CORS.
 */
export function getPorterchainApiBase(): string {
  const explicit = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "").trim().replace(/\/$/, "");
  if (explicit) return explicit;
  if (process.env.NODE_ENV === "development") return "http://localhost:8001";
  const site = (process.env.NEXT_PUBLIC_SITE_URL ?? "").trim().replace(/\/$/, "");
  return site || "https://porterchain.com";
}
