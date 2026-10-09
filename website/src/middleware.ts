import { clerkMiddleware } from "@clerk/nextjs/server";
import createMiddleware from "next-intl/middleware";
import type { NextFetchEvent, NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { isClerkClientShellPath } from "./lib/clerk-shell";
import { isKnownInvalidRoute } from "./lib/seo/known-route-guard";
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
    // Split sitemaps (/sitemap/{id}.xml) and the AI-crawler index must not get a locale redirect.
    pathname.startsWith("/sitemap/") ||
    pathname === "/llms.txt" ||
    pathname === "/ravi" ||
    pathname.startsWith("/ravi/") ||
    pathname === "/proof-of-resolution" ||
    pathname.startsWith("/proof-of-resolution/")
  );
}

function handleRequest(req: NextRequest) {
  if (shouldBypassIntl(req.nextUrl.pathname)) {
    return NextResponse.next();
  }
  const doubled = req.nextUrl.pathname.match(/^\/(en|fr)\/(en|fr)(\/.*)?$/);
  if (doubled) {
    // /en/en/... (double locale prefix) -> one canonical URL, permanent redirect.
    const url = req.nextUrl.clone();
    url.pathname = `/${doubled[2]}${doubled[3] ?? ""}`;
    return NextResponse.redirect(url, 308);
  }
  if (isKnownInvalidRoute(req.nextUrl.pathname, routing.locales)) {
    // Rewrite to an unmatched path so Next serves not-found.tsx with a real 404 status.
    const locale = req.nextUrl.pathname.split("/")[1];
    return NextResponse.rewrite(new URL(`/${locale}/__not-found__`, req.url));
  }
  const res = intlMiddleware(req);
  const first = req.nextUrl.pathname.split("/")[1];
  if (first === "fr") res.headers.set("Content-Language", "fr-CA");
  else if (first === "en") res.headers.set("Content-Language", "en-CA");
  return res;
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
