import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { clerkDevBypassEnabled, isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { hasClerkSessionHint } from "@porterchain/auth/clerkEdgeSession";
import { NextResponse } from "next/server";

const isPublic = createRouteMatcher(["/login(.*)", "/api/auth(.*)", "/impersonate(.*)"]);

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

/**
 * Clerk edge gate — light when session cookies exist (admin ``pc_staff_sid`` posture).
 * AccessGate + API Bearer still enforce identity; ``await auth()`` only when unsigned.
 */
export default clerkMiddleware(
  async (auth, req) => {
    // Local: API Bearer `dev` — skip Clerk edge when portal bypass is on.
    if (clerkDevBypassEnabled()) return;

    const devSessionId = req.cookies.get("pc_driver_dev_id")?.value;
    const hasDevSession = isDevLoginEnabled() && Boolean(devSessionId);
    const hasImpSession = Boolean(req.cookies.get("pc_imp_bearer")?.value?.startsWith("pc_imp_"));
    const sessionHint = hasClerkSessionHint(req.cookies);

    if (req.nextUrl.pathname === "/") {
      // Prefer cookie hints before auth() so `/` redirect stays cheap.
      if (sessionHint || hasDevSession || hasImpSession) {
        return NextResponse.redirect(new URL("/onboarding", req.url));
      }
      const { userId } = await auth();
      const dest = userId ? "/onboarding" : "/login";
      return NextResponse.redirect(new URL(dest, req.url));
    }

    if (isPublic(req)) return;

    if (hasDevSession || hasImpSession || sessionHint) {
      return NextResponse.next();
    }

    if (!clerkConfigured) {
      if (isDevelopmentBuild()) return;
      return NextResponse.redirect(new URL("/login", req.url));
    }

    const { userId } = await auth();
    if (userId) {
      return NextResponse.next();
    }

    if (req.nextUrl.pathname.startsWith("/api/")) {
      return NextResponse.json({ detail: "missing_bearer_token" }, { status: 401 });
    }

    const login = new URL("/login", req.url);
    const returnPath = `${req.nextUrl.pathname}${req.nextUrl.search}`;
    if (returnPath !== "/login" && !returnPath.startsWith("/login/")) {
      login.searchParams.set("redirect_url", returnPath);
    }
    return NextResponse.redirect(login);
  },
  { signInUrl: "/login" }
);

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
