import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { clerkDevBypassEnabled, isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { hasClerkSessionHint } from "@porterchain/auth/clerkEdgeSession";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher([
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/impersonate(.*)",
  // Embedded Shopify app: App Bridge session token is the identity, not Clerk.
  "/shopify-app(.*)",
]);

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim());

/**
 * Clerk edge gate — light when session cookies exist (admin ``pc_staff_sid`` posture).
 * AccessGate + API Bearer still enforce identity; ``await auth()`` only when unsigned.
 */
export default clerkMiddleware(
  async (auth, req) => {
    // Local: API Bearer `dev` — do not send the browser through Clerk.
    if (clerkDevBypassEnabled()) return;
    if (isPublicRoute(req)) return;
    if (req.cookies.get("pc_imp_bearer")?.value?.startsWith("pc_imp_")) return;

    if (!clerkConfigured) {
      if (isDevelopmentBuild()) return;
      return NextResponse.redirect(new URL("/sign-in", req.url));
    }

    // Signed-in hint → pass through (no session decrypt on every soft-nav / BFF hop).
    if (hasClerkSessionHint(req.cookies)) {
      return NextResponse.next();
    }

    const { userId } = await auth();
    if (userId) {
      return NextResponse.next();
    }

    // API must not HTML-redirect — match admin cookie middleware.
    if (req.nextUrl.pathname.startsWith("/api/")) {
      return NextResponse.json({ detail: "missing_bearer_token" }, { status: 401 });
    }

    const signIn = new URL("/sign-in", req.url);
    const returnPath = `${req.nextUrl.pathname}${req.nextUrl.search}`;
    if (returnPath !== "/sign-in" && !returnPath.startsWith("/sign-in/")) {
      signIn.searchParams.set("redirect_url", returnPath);
    }
    return NextResponse.redirect(signIn);
  },
  { signInUrl: "/sign-in" }
);

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest|txt)).*)",
    "/(api|trpc)(.*)",
  ],
};
