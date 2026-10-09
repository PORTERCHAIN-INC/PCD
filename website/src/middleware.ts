import { clerkMiddleware } from "@clerk/nextjs/server";
import createMiddleware from "next-intl/middleware";
import type { NextFetchEvent, NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { isClerkClientShellPath } from "./lib/clerk-shell";
import { isKnownInvalidRoute } from "./lib/seo/known-route-guard";
import { resolveUrlPolicy } from "./lib/seo/url-policy";
import { routing } from "./i18n/routing";

const intlMiddleware = createMiddleware(routing);

function isClerkConfigured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim() && process.env.CLERK_SECRET_KEY?.trim()
  );
}

function shouldBypassIntl(pathname: string): boolean {
  return (
    pathname === "/api" ||
    pathname.startsWith("/api/") ||
    pathname === "/opengraph-image" ||
    pathname === "/apple-icon" ||
    pathname === "/blog/rss.xml" ||
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

const CANONICAL_HOST = "porterchain.com";

function goneResponse(): NextResponse {
  return new NextResponse(
    '<!doctype html><title>410 Gone</title><h1>This page has been removed.</h1><p><a href="/en">Porterchain</a></p>',
    {
      status: 410,
      headers: { "content-type": "text/html; charset=utf-8", "x-robots-tag": "noindex" },
    }
  );
}

function handleRequest(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const host = (req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? "").toLowerCase();
  const wrongHost = host === `www.${CANONICAL_HOST}`;

  if (shouldBypassIntl(pathname) && !wrongHost && !pathname.endsWith("/")) {
    return NextResponse.next();
  }

  // One hop to the final URL: host + trailing slash + legacy prefixes + renamed slugs +
  // gated programmatic pages (lib/seo/url-policy.ts). next.config has
  // skipTrailingSlashRedirect so Next does not add a hop of its own before this runs.
  const policy = resolveUrlPolicy(pathname, search);
  if (policy.action === "gone") return goneResponse();
  if (policy.action === "notfound") {
    const locale = pathname.split("/")[1] === "fr" ? "fr" : "en";
    return NextResponse.rewrite(new URL(`/${locale}/__not-found__`, req.url));
  }
  if (policy.action === "redirect" || wrongHost) {
    const target = policy.action === "redirect" ? policy.location : `${pathname}${search}`;
    const url = new URL(target, req.url);
    if (wrongHost) {
      url.host = CANONICAL_HOST;
      url.protocol = "https:";
      url.port = "";
    }
    return NextResponse.redirect(url, 301);
  }
  if (shouldBypassIntl(pathname)) {
    return NextResponse.next();
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
    "/((?!_next|sitemap\\.xml|robots\\.txt|[^?]*\\.(?:css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
