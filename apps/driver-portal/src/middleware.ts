import { authDevBypassEnabled, isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { hasSessionCookie } from "@porterchain/auth/oidc";
import { portalMiddleware } from "@porterchain/auth/oidc/next";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Email-only driver login. The `pc_driver_dev_id` cookie it accepts is forgeable,
 * so a production build must never honour it whatever the variable says (BJ).
 */
function isDevLoginEnabled(): boolean {
  if (!isDevelopmentBuild()) return false;
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "false") return false;
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "true") return true;
  const appEnv = (process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV ?? "").trim();
  return appEnv === "local" || appEnv === "development";
}

const hasDevSession = (req: NextRequest) =>
  isDevLoginEnabled() && Boolean(req.cookies.get("pc_driver_dev_id")?.value);
const hasImp = (req: NextRequest) =>
  Boolean(req.cookies.get("pc_imp_bearer")?.value?.startsWith("pc_imp_"));

// Keycloak edge gate (L36); AccessGate + API Bearer still enforce identity and roles.
const gate = portalMiddleware({
  publicPaths: ["/login", "/api/auth", "/impersonate"],
  signInPath: "/login",
  allow: hasDevSession,
  devPassThrough: () => authDevBypassEnabled(),
});

export default async function middleware(req: NextRequest) {
  if (req.nextUrl.pathname === "/" && !authDevBypassEnabled()) {
    const signedIn = hasSessionCookie(req.cookies) || hasDevSession(req) || hasImp(req);
    return NextResponse.redirect(new URL(signedIn ? "/onboarding" : "/login", req.url));
  }
  return gate(req);
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest|txt)).*)",
    "/(api|trpc)(.*)",
  ],
};
