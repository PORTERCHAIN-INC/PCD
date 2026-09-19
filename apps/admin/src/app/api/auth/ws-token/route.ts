import { NextRequest, NextResponse } from "next/server";

/**
 * Ephemeral Bearer for WebSocket clients (notifications).
 * Prefer BFF for HTTP; WS to :8001 cannot read the HttpOnly admin cookie.
 */
export async function GET(req: NextRequest) {
  const sid = req.cookies.get("pc_staff_sid")?.value?.trim();
  if (!sid) {
    return NextResponse.json({ detail: "missing_bearer_token" }, { status: 401 });
  }
  return NextResponse.json({ token: `staff_sess_${sid}` });
}
