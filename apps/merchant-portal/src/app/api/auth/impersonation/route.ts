import { NextRequest, NextResponse } from "next/server";

const COOKIE = "pc_imp_bearer";
const API_BASE = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
  /\/$/,
  ""
);

/** Establish / clear HttpOnly impersonation cookie for driver BFF. */
export async function POST(request: NextRequest) {
  const body = (await request.json().catch(() => ({}))) as { token?: string };
  const token = (body.token || "").trim();
  if (!token.startsWith("pc_imp_")) {
    return NextResponse.json({ detail: "invalid_impersonation_token" }, { status: 400 });
  }
  const peek = await fetch(`${API_BASE}/v1/auth/impersonation/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!peek.ok) {
    return NextResponse.json({ detail: "impersonation_expired" }, { status: 401 });
  }
  const data = await peek.json();
  const res = NextResponse.json({ ok: true, ...data });
  res.cookies.set(COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: Math.max(60, Number(data.seconds_remaining) || 900),
  });
  return res;
}

export async function GET() {
  return NextResponse.json({ ok: true });
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.set(COOKIE, "", { httpOnly: true, path: "/", maxAge: 0 });
  return res;
}
