function resolveApiUrl() {
  const raw = process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL?.trim();
  if (raw) return raw.replace(/\/$/, "");
  return process.env.NODE_ENV === "development"
    ? "http://localhost:8001"
    : "https://api.porterchain.com";
}

export const publicEnv = {
  porterchainApiUrl: resolveApiUrl(),
  websiteUrl: (
    process.env.NEXT_PUBLIC_WEBSITE_URL ??
    (process.env.NODE_ENV === "development" ? "http://localhost:3000" : "https://porterchain.com")
  ).replace(/\/$/, ""),
  keycloakClientId: (process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "").trim(),
  appEnv: (process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV ?? "production").trim(),
} as const;

export function isLocalDev() {
  return publicEnv.appEnv === "local" || publicEnv.appEnv === "development";
}

export function isAuthConfigured() {
  return publicEnv.keycloakClientId.length > 0;
}
