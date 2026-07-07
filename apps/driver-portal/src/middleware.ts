import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const ACCESS_COOKIE = "driver_access_token";

const PUBLIC_PREFIXES = ["/login", "/api/auth/login", "/api/auth/driver-session"];

function isPublic(pathname: string) {
  return PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** Porterchain driver JWT cookie guard — Clerk is used only at /login. */
export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (isPublic(pathname)) return NextResponse.next();
  if (pathname.startsWith("/api/")) return NextResponse.next();

  const hasSession = Boolean(req.cookies.get(ACCESS_COOKIE)?.value);
  if (!hasSession) {
    const login = new URL("/login", req.url);
    login.searchParams.set("redirect_url", pathname);
    return NextResponse.redirect(login);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
  ],
};
