export const publicEnv = {
  porterchainApiUrl: (
    process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ??
    (process.env.NODE_ENV === "development"
      ? "http://localhost:8001"
      : "https://api.porterchain.com")
  ).replace(/\/$/, ""),
  keycloakClientId: (process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "").trim(),
  websiteUrl: (
    process.env.NEXT_PUBLIC_WEBSITE_URL ??
    (process.env.NODE_ENV === "development" ? "http://localhost:3000" : "https://porterchain.com")
  ).replace(/\/$/, ""),
} as const;

export function isAuthConfigured(): boolean {
  return publicEnv.keycloakClientId.length > 0;
}
