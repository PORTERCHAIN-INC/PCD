import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublic = createRouteMatcher(["/sign-in(.*)", "/api/auth/session"]);

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim());

export default clerkMiddleware(
  async (auth, req) => {
    if (req.nextUrl.pathname === "/") {
      const { userId } = await auth();
      const dest = userId ? "/dashboard" : "/sign-in";
      return NextResponse.redirect(new URL(dest, req.url));
    }

    if (isPublic(req)) return;

    if (clerkConfigured) {
      const { userId } = await auth();
      if (!userId) {
        // Manual redirect keeps auth on admin.porterchain.com. auth.protect() can still
        // bounce to accounts.admin.porterchain.com (403) and cause flicker loops.
        const signIn = new URL("/sign-in", req.url);
        const returnPath = `${req.nextUrl.pathname}${req.nextUrl.search}`;
        if (returnPath !== "/sign-in" && !returnPath.startsWith("/sign-in/")) {
          signIn.searchParams.set("redirect_url", returnPath);
        }
        return NextResponse.redirect(signIn);
      }
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
