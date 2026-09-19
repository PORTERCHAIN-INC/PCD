import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PREFIXES = [
  "/sign-in",
  "/activate-staff",
  "/api/auth/staff-session",
  "/api/auth/session",
  "/api/auth/ws-token",
];

function isPublic(pathname: string): boolean {
  return PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/**
 * Staff IdP only — one auth path in every environment.
 * Development Local Super Admin mints a real ``pc_staff_sid`` cookie (same as activate).
 */
export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const staffSid = req.cookies.get("pc_staff_sid")?.value;

  if (pathname === "/") {
    const dest = staffSid ? "/dashboard" : "/sign-in";
    return NextResponse.redirect(new URL(dest, req.url));
  }

  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  if (staffSid) {
    return NextResponse.next();
  }

  // API routes must not HTML-redirect — return JSON 401 for BFF/fetch callers.
  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ detail: "missing_bearer_token" }, { status: 401 });
  }

  const signIn = new URL("/sign-in", req.url);
  const returnPath = `${pathname}${req.nextUrl.search}`;
  if (returnPath !== "/sign-in" && !returnPath.startsWith("/sign-in/")) {
    signIn.searchParams.set("redirect_url", returnPath);
  }
  return NextResponse.redirect(signIn);
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
