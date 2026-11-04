/** Keycloak OIDC endpoints (L36): /auth/login, register, callback, logout, session, account. */
// Always dynamic: handleAuthRoute reads the request (cacheComponents forbids route segment `dynamic`).
import { handleAuthRoute } from "@porterchain/auth/oidc/next";

export const GET = handleAuthRoute;
