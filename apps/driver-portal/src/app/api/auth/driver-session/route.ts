import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const ACCESS_COOKIE = "driver_access_token";

/** Porterchain driver JWT cookie check — not Clerk session (see clerkMiddleware). */
export async function GET() {
  const jar = await cookies();
  return NextResponse.json({ authenticated: Boolean(jar.get(ACCESS_COOKIE)?.value) });
}
