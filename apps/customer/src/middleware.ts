import { authDevBypassEnabled } from "@porterchain/auth/devBypass";
import { portalMiddleware } from "@porterchain/auth/oidc/next";

// /track only redirects to the public website tracking page (signed link when signed in).
// Keycloak edge gate (L36); AccessGate + API Bearer still enforce identity and roles.
export default portalMiddleware({
  publicPaths: ["/sign-in", "/sign-up", "/impersonate", "/track", "/welcome"],
  // Local: API Bearer `dev`. Production bundles fold authDevBypassEnabled() to false.
  devPassThrough: () => authDevBypassEnabled(),
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest|txt)).*)",
    "/(api|trpc)(.*)",
  ],
};
