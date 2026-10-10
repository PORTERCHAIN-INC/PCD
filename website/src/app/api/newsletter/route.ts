import { NextResponse } from "next/server";
import { getPorterchainApiBase } from "@/lib/api-base";

/** Newsletter sign-up → API double opt-in (sends one confirmation email). */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const apiKey = (process.env.PUBLIC_INGEST_API_KEY ?? "").trim();
    const forwardedFor =
      request.headers.get("x-forwarded-for") ?? request.headers.get("x-real-ip") ?? "";
    const res = await fetch(`${getPorterchainApiBase()}/v1/public/newsletter/subscribe`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(apiKey ? { "X-Ingest-Key": apiKey } : {}),
        ...(forwardedFor ? { "X-Forwarded-For": forwardedFor } : {}),
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const error = typeof data.detail === "string" ? data.detail : "subscribe_failed";
      return NextResponse.json({ error }, { status: res.status });
    }
    return NextResponse.json(data, { status: 202 });
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }
}
