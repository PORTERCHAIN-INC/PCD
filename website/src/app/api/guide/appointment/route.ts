import { NextResponse } from "next/server";
import { bookGuideAppointment } from "@/lib/home/guide-api";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const result = await bookGuideAppointment(body);
    if (!result.ok) {
      const status = result.error === "phone_required" ? 422 : 400;
      return NextResponse.json({ error: result.error }, { status });
    }
    return NextResponse.json(result.data, { status: 201 });
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }
}
