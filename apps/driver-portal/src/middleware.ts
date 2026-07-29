import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublic = createRouteMatcher(["/login(.*)", "/api/auth(.*)"]);

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim());

/** Clerk session guard — same pattern as other portals (no Porterchain JWT cookies). */
export default clerkMiddleware(
  async (auth, req) => {
    if (req.nextUrl.pathname === "/") {
      const { userId } = await auth();
      const dest = userId ? "/onboarding" : "/login";
      return NextResponse.redirect(new URL(dest, req.url));
    }

    if (isPublic(req)) return;

    if (clerkConfigured) {
      const { userId } = await auth();
      if (!userId) {
        const login = new URL("/login", req.url);
        const returnPath = `${req.nextUrl.pathname}${req.nextUrl.search}`;
        if (returnPath !== "/login" && !returnPath.startsWith("/login/")) {
          login.searchParams.set("redirect_url", returnPath);
        }
        return NextResponse.redirect(login);
      }
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
