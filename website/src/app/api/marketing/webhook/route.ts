import { NextResponse } from "next/server";

/** Optional CRM/Make/Zapier mirror for conversion events. */
export async function POST(req: Request) {
  const webhook = (process.env.MARKETING_EVENT_WEBHOOK_URL ?? "").trim();
  if (!webhook) {
    return NextResponse.json({ ok: false, skipped: "webhook_unset" }, { status: 501 });
  }

  let payload: unknown;
  try {
    payload = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const res = await fetch(webhook, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return NextResponse.json({ ok: res.ok, status: res.status }, { status: res.ok ? 200 : 502 });
}
