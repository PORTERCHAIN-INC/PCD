import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { NextResponse } from "next/server";

const isPublic = createRouteMatcher(["/login(.*)", "/api/auth(.*)"]);

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim());

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

/** Clerk session guard — local also accepts pc_driver_dev_id cookie (email picker). */
export default clerkMiddleware(
  async (auth, req) => {
    const devSessionId = req.cookies.get("pc_driver_dev_id")?.value;
    const hasDevSession = isDevLoginEnabled() && Boolean(devSessionId);

    if (req.nextUrl.pathname === "/") {
      const { userId } = await auth();
      const dest = userId || hasDevSession ? "/onboarding" : "/login";
      return NextResponse.redirect(new URL(dest, req.url));
    }

    if (isPublic(req)) return;

    if (hasDevSession) {
      return NextResponse.next();
    }

    // Missing publishable key must fail closed in a shipped build (BJ).
    if (!clerkConfigured) {
      if (isDevelopmentBuild()) return;
      return NextResponse.redirect(new URL("/login", req.url));
    }

    const { userId } = await auth();
    if (!userId) {
      const login = new URL("/login", req.url);
      const returnPath = `${req.nextUrl.pathname}${req.nextUrl.search}`;
      if (returnPath !== "/login" && !returnPath.startsWith("/login/")) {
        login.searchParams.set("redirect_url", returnPath);
      }
      return NextResponse.redirect(login);
    }
  },
  { signInUrl: "/login" }
);

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
