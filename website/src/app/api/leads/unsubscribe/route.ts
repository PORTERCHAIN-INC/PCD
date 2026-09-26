import { NextResponse } from "next/server";
import { getPorterchainApiBase } from "@/lib/api-base";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const apiBase = getPorterchainApiBase();
    const res = await fetch(`${apiBase}/v1/public/leads/unsubscribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      const message =
        typeof detail.detail === "string"
          ? detail.detail
          : typeof detail.error === "string"
            ? detail.error
            : "unsubscribe_failed";
      return NextResponse.json({ error: message }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }
}
