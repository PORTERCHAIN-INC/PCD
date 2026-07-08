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
]);

function isClerkConfigured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim() && process.env.CLERK_SECRET_KEY?.trim()
  );
}

function shouldBypassIntl(pathname: string): boolean {
  return (
    pathname.startsWith("/api") ||
    pathname === "/sitemap.xml" ||
    pathname === "/robots.txt" ||
    pathname === "/ravi" ||
    pathname.startsWith("/ravi/")
  );
}

function handleRequest(req: NextRequest) {
  if (shouldBypassIntl(req.nextUrl.pathname)) {
    return NextResponse.next();
  }
  return intlMiddleware(req);
}

export default isClerkConfigured()
  ? clerkMiddleware(async (_auth, req) => handleRequest(req))
  : handleRequest;

export const config = {
  matcher: [
    // Skip SEO/crawler files — Clerk and locale middleware must not touch these.
    "/((?!_next|sitemap\\.xml|robots\\.txt|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
