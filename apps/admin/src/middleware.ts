import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PREFIXES = [
  "/sign-in",
  "/activate-staff",
  "/api/auth/staff-session",
  "/api/auth/session",
];

function isPublic(pathname: string): boolean {
  return PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** Staff IdP only — Clerk middleware removed (canvas Phase 5). */
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

  // Local API bypass: allow shell without cookie when NEXT_PUBLIC_CLERK_DEV_BYPASS=true
  if (process.env.NEXT_PUBLIC_CLERK_DEV_BYPASS === "true") {
    return NextResponse.next();
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
