import { clerkMiddleware } from "@clerk/nextjs/server";
import createMiddleware from "next-intl/middleware";
import type { NextFetchEvent, NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { isClerkClientShellPath } from "./lib/clerk-shell";
import { routing } from "./i18n/routing";

const intlMiddleware = createMiddleware(routing);

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

const clerkHandler = clerkMiddleware(async (_auth, req) => handleRequest(req));

export default function middleware(req: NextRequest, event: NextFetchEvent) {
  if (!isClerkConfigured()) {
    return handleRequest(req);
  }

  if (!isClerkClientShellPath(req.nextUrl.pathname)) {
    return handleRequest(req);
  }

  return clerkHandler(req, event);
}

export const config = {
  matcher: [
    // Skip SEO/crawler files — Clerk and locale middleware must not touch these.
    "/((?!_next|sitemap\\.xml|robots\\.txt|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
