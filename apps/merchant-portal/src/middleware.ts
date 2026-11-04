import { authDevBypassEnabled } from "@porterchain/auth/devBypass";
import { portalMiddleware } from "@porterchain/auth/oidc/next";

// Keycloak edge gate (L36); AccessGate + API Bearer still enforce identity and roles.
// /shopify-app uses App Bridge session tokens, not the portal session.
export default portalMiddleware({
  publicPaths: ["/sign-in", "/sign-up", "/impersonate", "/api/auth-telemetry", "/shopify-app"],
  // Local: API Bearer `dev`. Production bundles fold authDevBypassEnabled() to false.
  devPassThrough: () => authDevBypassEnabled(),
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest|txt)).*)",
    "/(api|trpc)(.*)",
  ],
};
