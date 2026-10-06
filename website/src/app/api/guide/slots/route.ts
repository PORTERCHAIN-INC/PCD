import { NextResponse } from "next/server";
import { listGuideSlots } from "@/lib/home/guide-api";

export async function GET(request: Request) {
  const meetingType =
    new URL(request.url).searchParams.get("meeting_type") === "meeting" ? "meeting" : "call";
  const result = await listGuideSlots(meetingType);
  if (!result.ok) {
    return NextResponse.json({ error: result.error }, { status: 502 });
  }
  return NextResponse.json(result.data);
}
