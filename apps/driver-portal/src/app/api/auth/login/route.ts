import { NextRequest, NextResponse } from "next/server";

const API_BASE = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
  /\/$/,
  ""
);

const ACCESS_COOKIE = "driver_access_token";
const REFRESH_COOKIE = "driver_refresh_token";

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export async function POST(request: NextRequest) {
  const body = (await request.json()) as { email?: string; clerkToken?: string };
  if (!body.email) {
    return NextResponse.json({ detail: "email_required" }, { status: 400 });
  }

  const res = await fetch(`${API_BASE}/driver-api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(body.clerkToken ? { Authorization: `Bearer ${body.clerkToken}` } : {}),
    },
    body: JSON.stringify({ email: body.email }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(data, { status: res.status });
  }

  const response = NextResponse.json({ ok: true, driver_id: data.driver_id });
  const accessMaxAge = typeof data.expires_in === "number" ? data.expires_in : 60 * 60;
  response.cookies.set(ACCESS_COOKIE, data.access_token, cookieOptions(accessMaxAge));
  response.cookies.set(REFRESH_COOKIE, data.refresh_token, cookieOptions(60 * 60 * 24 * 30));
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set(ACCESS_COOKIE, "", { ...cookieOptions(0), maxAge: 0 });
  response.cookies.set(REFRESH_COOKIE, "", { ...cookieOptions(0), maxAge: 0 });
  return response;
}
