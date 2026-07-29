import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

/** Clerk session presence — replaces driver_access_token cookie check. */
export async function GET() {
  const { userId } = await auth();
  return NextResponse.json({ authenticated: Boolean(userId) });
}
