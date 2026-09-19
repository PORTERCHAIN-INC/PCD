import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { clerkDevBypassEnabled, isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher(["/sign-in(.*)", "/sign-up(.*)"]);

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim());

export default clerkMiddleware(
  async (auth, req) => {
    // Local: API Bearer `dev` — do not send the browser through Clerk. A
    // production build never takes this branch, whatever the variable says (BJ).
    if (clerkDevBypassEnabled()) return;
    if (isPublicRoute(req)) return;
    // Missing publishable key must fail closed, not open the portal. Locally we
    // let the shell render so the sign-in page can explain the misconfiguration.
    if (!clerkConfigured) {
      if (isDevelopmentBuild()) return;
      return NextResponse.redirect(new URL("/sign-in", req.url));
    }

    const { userId } = await auth();
    if (!userId) {
      const signIn = new URL("/sign-in", req.url);
      const returnPath = `${req.nextUrl.pathname}${req.nextUrl.search}`;
      if (returnPath !== "/sign-in" && !returnPath.startsWith("/sign-in/")) {
        signIn.searchParams.set("redirect_url", returnPath);
      }
      return NextResponse.redirect(signIn);
    }
  },
  { signInUrl: "/sign-in" }
);

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
