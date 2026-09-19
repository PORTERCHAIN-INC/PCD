import { NextRequest, NextResponse } from "next/server";

const COOKIE = "pc_staff_sid";
const MAX_AGE = 60 * 60 * 12;

function cookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: MAX_AGE,
  };
}

/** Set admin-origin staff session cookie (middleware gate + same-origin probe). */
export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as {
    bearer_token?: string;
    session_id?: string;
  };
  let sessionId = (body.session_id || "").trim();
  const bearer = (body.bearer_token || "").trim();
  if (!sessionId && bearer.startsWith("staff_sess_")) {
    sessionId = bearer.slice("staff_sess_".length);
  }
  if (!sessionId) {
    return NextResponse.json({ detail: "session_id_required" }, { status: 400 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(COOKIE, sessionId, cookieOptions());
  return res;
}

export async function GET(req: NextRequest) {
  const sid = req.cookies.get(COOKIE)?.value;
  return NextResponse.json({ authenticated: Boolean(sid) });
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.set(COOKIE, "", { ...cookieOptions(), maxAge: 0 });
  return res;
}
