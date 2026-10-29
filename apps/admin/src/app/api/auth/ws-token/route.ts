import { NextResponse } from "next/server";
import { auth } from "@porterchain/auth/oidc/next";

/** Access token for the notifications WebSocket (the browser cannot read the session cookie). */
export async function GET() {
  const token = await (await auth()).getToken();
  if (!token) {
    return NextResponse.json({ detail: "missing_bearer_token" }, { status: 401 });
  }
  return NextResponse.json({ token }, { headers: { "Cache-Control": "no-store" } });
}
