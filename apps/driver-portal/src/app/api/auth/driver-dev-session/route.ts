import { NextRequest, NextResponse } from "next/server";

const API_BASE = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
  /\/$/,
  ""
);

export const DRIVER_DEV_COOKIE = "pc_driver_dev_id";

function isDevLoginEnabled(): boolean {
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "false") return false;
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "true") return true;
  const appEnv = (process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV ?? "").trim();
  return appEnv === "local" || appEnv === "development";
}

/** Local email-picker session — sets httpOnly driver id cookie for BFF X-Driver-Id. */
export async function POST(request: NextRequest) {
  if (!isDevLoginEnabled()) {
    return NextResponse.json({ detail: "driver_dev_login_disabled" }, { status: 404 });
  }
  const body = (await request.json().catch(() => ({}))) as { email?: string };
  const email = (body.email ?? "").trim().toLowerCase();
  if (!email) {
    return NextResponse.json({ detail: "email_required" }, { status: 400 });
  }

  const upstream = await fetch(`${API_BASE}/driver-api/v1/auth/dev-login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: ["Bearer", "dev"].join(" "),
    },
    body: JSON.stringify({ email }),
  });
  const payload = await upstream.json().catch(() => ({}));
  if (!upstream.ok) {
    return NextResponse.json(payload, { status: upstream.status });
  }

  const driverId = String((payload as { driver_id?: string }).driver_id ?? "");
  if (!driverId) {
    return NextResponse.json({ detail: "driver_id_missing" }, { status: 500 });
  }

  const res = NextResponse.json({
    ok: true,
    driver_id: driverId,
    email: (payload as { email?: string }).email,
    full_name: (payload as { full_name?: string }).full_name,
  });
  res.cookies.set(DRIVER_DEV_COOKIE, driverId, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 12,
  });
  return res;
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.set(DRIVER_DEV_COOKIE, "", { httpOnly: true, path: "/", maxAge: 0 });
  return res;
}

export async function GET() {
  if (!isDevLoginEnabled()) {
    return NextResponse.json({ detail: "driver_dev_login_disabled" }, { status: 404 });
  }
  const upstream = await fetch(`${API_BASE}/driver-api/v1/auth/dev-drivers`, {
    headers: { Authorization: ["Bearer", "dev"].join(" ") },
  });
  const payload = await upstream.json().catch(() => []);
  return NextResponse.json(payload, { status: upstream.status });
}
