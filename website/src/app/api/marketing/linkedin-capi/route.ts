import { NextResponse } from "next/server";

/** LinkedIn Conversions API stub — dark until LINKEDIN_CAPI_TOKEN is set. */
export async function POST(req: Request) {
  const token = (process.env.LINKEDIN_CAPI_TOKEN ?? "").trim();
  if (!token) {
    return NextResponse.json({ ok: false, skipped: "linkedin_capi_unset" }, { status: 501 });
  }

  let payload: unknown;
  try {
    payload = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const webhook = (process.env.MARKETING_EVENT_WEBHOOK_URL ?? "").trim();
  if (webhook) {
    await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: "linkedin_capi_stub", payload }),
    }).catch(() => undefined);
  }

  return NextResponse.json({ ok: true, forwarded: Boolean(webhook) });
}
