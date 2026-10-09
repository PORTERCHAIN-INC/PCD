import { NextResponse } from "next/server";
import { getPorterchainApiBase } from "@/lib/api-base";

/** Instant price for the website calculator. Proxies the public estimate API (no PII). */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const forwardedFor =
      request.headers.get("x-forwarded-for") ?? request.headers.get("x-real-ip") ?? "";
    const res = await fetch(`${getPorterchainApiBase()}/v1/public/estimate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(forwardedFor ? { "X-Forwarded-For": forwardedFor } : {}),
      },
      body: JSON.stringify({
        pickup_postal: String(body?.pickup_postal ?? ""),
        dropoff_postal: String(body?.dropoff_postal ?? ""),
        vehicle_class: String(body?.vehicle_class ?? "sedan_suv"),
      }),
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const error = typeof data.detail === "string" ? data.detail : "estimate_failed";
      return NextResponse.json({ error }, { status: res.status });
    }
    return NextResponse.json(data, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }
}
