import { NextResponse } from "next/server";
import { getPorterchainApiBase } from "@/lib/api-base";

/** Confirmation link click → API marks the subscriber confirmed. */
export async function POST(request: Request) {
  try {
    const { token } = (await request.json()) as { token?: string };
    if (!token || typeof token !== "string") {
      return NextResponse.json({ error: "token_required" }, { status: 400 });
    }
    const forwardedFor =
      request.headers.get("x-forwarded-for") ?? request.headers.get("x-real-ip") ?? "";
    const res = await fetch(`${getPorterchainApiBase()}/v1/public/newsletter/confirm`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(forwardedFor ? { "X-Forwarded-For": forwardedFor } : {}),
      },
      body: JSON.stringify({ token }),
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.ok ? 200 : res.status });
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }
}
