import { NextResponse } from "next/server";
import { getPorterchainApiBase } from "@/lib/api-base";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const apiKey = (process.env.PUBLIC_INGEST_API_KEY ?? "").trim();
    const apiBase = getPorterchainApiBase();

    const res = await fetch(`${apiBase}/v1/public/inquiries`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(apiKey ? { "X-Ingest-Key": apiKey } : {}),
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      const message =
        typeof detail.detail === "string"
          ? detail.detail
          : typeof detail.error === "string"
            ? detail.error
            : "ingest_failed";
      return NextResponse.json({ error: message }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data, { status: 201 });
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }
}
