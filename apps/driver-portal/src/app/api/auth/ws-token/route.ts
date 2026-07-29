import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

/** Return Clerk JWT for websocket clients — no Porterchain cookie JWT. */
export async function GET() {
  const { getToken, userId } = await auth();
  if (!userId) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }
  const token = await getToken();
  if (!token) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }
  return NextResponse.json({ token });
}
