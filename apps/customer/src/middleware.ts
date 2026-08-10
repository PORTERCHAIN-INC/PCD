import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher(["/sign-in(.*)", "/sign-up(.*)"]);

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim());

export default clerkMiddleware(
  async (auth, req) => {
    if (isPublicRoute(req)) return;
    if (!clerkConfigured) return;

    const { userId } = await auth();
    if (!userId) {
      const signIn = new URL("/sign-in", req.url);
      const returnPath = `${req.nextUrl.pathname}${req.nextUrl.search}`;
      if (
        returnPath !== "/sign-in" &&
        !returnPath.startsWith("/sign-in/") &&
        returnPath !== "/sign-up" &&
        !returnPath.startsWith("/sign-up/")
      ) {
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
