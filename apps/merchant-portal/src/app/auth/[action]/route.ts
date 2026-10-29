/** Keycloak OIDC endpoints (L36): /auth/login, register, callback, logout, session, account. */
import { handleAuthRoute } from "@porterchain/auth/oidc/next";

export const dynamic = "force-dynamic";
export const GET = handleAuthRoute;
