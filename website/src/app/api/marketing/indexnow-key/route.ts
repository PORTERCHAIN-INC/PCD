import { NextResponse } from "next/server";
import { getIndexNowKey } from "@/lib/marketing/indexnow";

/** Public key location for IndexNow verification. */
export async function GET() {
  const key = getIndexNowKey();
  if (!key) {
    return new NextResponse("INDEXNOW_KEY unset", { status: 404 });
  }
  return new NextResponse(key, {
    status: 200,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
