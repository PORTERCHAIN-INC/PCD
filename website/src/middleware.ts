import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import createMiddleware from "next-intl/middleware";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { routing } from "./i18n/routing";

const intlMiddleware = createMiddleware(routing);

const isPublicRoute = createRouteMatcher([
  "/:locale/login(.*)",
  "/login(.*)",
  "/:locale/book/success(.*)",
  "/book/success(.*)",
  "/:locale/portal/customer/sign-in(.*)",
  "/portal/customer/sign-in(.*)",
]);

const isCustomerPortalRoute = createRouteMatcher([
  "/:locale/portal/customer",
  "/:locale/portal/customer/(.*)",
  "/portal/customer",
  "/portal/customer/(.*)",
]);

function isClerkConfigured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim() && process.env.CLERK_SECRET_KEY?.trim()
  );
}

function handleRequest(req: NextRequest) {
  if (req.nextUrl.pathname.startsWith("/api")) {
    return NextResponse.next();
  }
  return intlMiddleware(req);
}

export default isClerkConfigured()
  ? clerkMiddleware(async (auth, req) => {
      if (isPublicRoute(req)) {
        return handleRequest(req);
      }
      // Legacy embedded portal — client-side gate redirects to /login (not Clerk hosted).
      if (isCustomerPortalRoute(req)) {
        return handleRequest(req);
      }
      return handleRequest(req);
    })
  : handleRequest;

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
