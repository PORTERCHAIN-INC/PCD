import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";
import { isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { DRIVER_DEV_COOKIE } from "@/lib/driver-dev-cookie";

function isDevLoginEnabled(): boolean {
  if (!isDevelopmentBuild()) return false;
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "false") return false;
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "true") return true;
  const appEnv = (process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV ?? "").trim();
  return appEnv === "local" || appEnv === "development";
}

/** Clerk session, or local email-picker cookie (`pc_driver_dev_id`). */
export async function GET(request: NextRequest) {
  const { userId } = await auth();
  if (userId) {
    return NextResponse.json({ authenticated: true });
  }
  if (!isDevLoginEnabled()) {
    return NextResponse.json({ authenticated: false });
  }
  return NextResponse.json({
    authenticated: Boolean(request.cookies.get(DRIVER_DEV_COOKIE)?.value),
  });
}
