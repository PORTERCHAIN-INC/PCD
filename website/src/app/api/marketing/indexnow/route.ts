import { NextResponse } from "next/server";
import { pingIndexNow } from "@/lib/marketing/indexnow";

/**
 * Optional IndexNow trigger. Body: { urls: string[] }
 * No-op without INDEXNOW_KEY. Protect in production via deploy hooks only.
 */
export async function POST(req: Request) {
  const key = (process.env.INDEXNOW_KEY ?? "").trim();
  if (!key) {
    return NextResponse.json({ ok: false, skipped: "INDEXNOW_KEY unset" }, { status: 501 });
  }

  let urls: string[] = [];
  try {
    const body = (await req.json()) as { urls?: string[] };
    urls = Array.isArray(body.urls) ? body.urls.filter((u) => typeof u === "string") : [];
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const result = await pingIndexNow(urls);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
