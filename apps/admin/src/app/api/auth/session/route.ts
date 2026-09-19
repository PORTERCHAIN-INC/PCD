import { NextRequest, NextResponse } from "next/server";

/**
 * Session probe for sign-in — staff IdP cookie only (Clerk retired from admin).
 */
export async function GET(req: NextRequest) {
  const signedIn = Boolean(req.cookies.get("pc_staff_sid")?.value);
  return NextResponse.json({ signedIn });
}
