import { NextResponse } from "next/server";
import { computeQuote, isQuoteError } from "@/lib/quote/engine";
import type { QuoteRequest } from "@/lib/quote/types";

export const runtime = "nodejs";
export const maxDuration = 10;

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as QuoteRequest;
    const result = await computeQuote(body);

    if (isQuoteError(result)) {
      const status =
        result.code === "TIMEOUT"
          ? 504
          : result.code === "OUT_OF_SERVICE_AREA" || result.code === "NO_VEHICLE_FIT"
            ? 422
            : 400;

      return NextResponse.json(result, { status });
    }

    return NextResponse.json(result, {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
        "X-Quote-Computed-Ms": String(result.computedInMs),
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Invalid request body", code: "INVALID_INPUT" },
      { status: 400 }
    );
  }
}
