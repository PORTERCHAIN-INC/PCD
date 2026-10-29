import { NextResponse, type NextRequest } from "next/server";
import { authDevBypassEnabled } from "@porterchain/auth/devBypass";
import { portalMiddleware } from "@porterchain/auth/oidc/next";

// Keycloak `pc-admin` session gate (MFA enforced by the realm). The API re-checks the JWT,
// AdminUser role and SpiceDB on every call.
const gate = portalMiddleware({
  publicPaths: ["/sign-in"],
  // Local only: API Bearer `dev`. Production bundles fold authDevBypassEnabled() to false.
  devPassThrough: () => authDevBypassEnabled(),
});

export default async function middleware(req: NextRequest) {
  if (req.nextUrl.pathname === "/") return NextResponse.redirect(new URL("/today", req.url));
  return gate(req);
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest|txt)).*)",
    "/(api|trpc)(.*)",
  ],
};
