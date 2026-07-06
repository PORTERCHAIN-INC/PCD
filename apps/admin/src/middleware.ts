import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublic = createRouteMatcher(["/sign-in(.*)"]);

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim());

export default clerkMiddleware(
  async (auth, req) => {
    // Root "/" statically redirects to /dashboard; resolve here so unauthenticated
    // users go straight to the in-app sign-in instead of bouncing via Account Portal.
    if (req.nextUrl.pathname === "/") {
      const { userId } = await auth();
      const dest = userId ? "/dashboard" : "/sign-in";
      return NextResponse.redirect(new URL(dest, req.url));
    }

    if (isPublic(req)) return;

    if (clerkConfigured) {
      // unauthenticatedUrl forces the app's own /sign-in page. Without it, auth.protect()
      // redirects to Clerk's hosted Account Portal (accounts.admin.porterchain.com),
      // which loops on redirect_url=/ and causes the sign-in page to refresh repeatedly.
      await auth.protect({
        unauthenticatedUrl: new URL("/sign-in", req.url).toString(),
      });
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
