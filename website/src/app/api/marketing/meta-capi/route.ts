import { NextResponse } from "next/server";

/**
 * Meta Conversions API stub — dark until META_CAPI_ACCESS_TOKEN + pixel id are set.
 * Call from quote success clients with hashed user data when marketing consent granted.
 */
export async function POST(req: Request) {
  const token = (process.env.META_CAPI_ACCESS_TOKEN ?? "").trim();
  const pixelId = (process.env.NEXT_PUBLIC_META_PIXEL_ID ?? "").trim();
  if (!token || !pixelId) {
    return NextResponse.json({ ok: false, skipped: "meta_capi_unset" }, { status: 501 });
  }

  let payload: unknown;
  try {
    payload = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const res = await fetch(`https://graph.facebook.com/v21.0/${pixelId}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      data: [payload],
      access_token: token,
    }),
  });

  return NextResponse.json({ ok: res.ok, status: res.status }, { status: res.ok ? 200 : 502 });
}
