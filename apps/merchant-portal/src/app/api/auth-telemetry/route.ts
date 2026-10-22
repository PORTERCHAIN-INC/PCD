import { NextResponse } from "next/server";
import { authTelemetryLogLine } from "@porterchain/auth/authTelemetry";

/**
 * Sign-in / sign-up failures the browser saw (Clerk not loading, bot-check stall,
 * offline, Clerk form errors). One structured log line each: grep
 * `auth_client_failure` in the container logs. No email, password or code.
 */
export async function POST(request: Request) {
  const raw = await request.text().catch(() => "");
  if (raw.length > 2000) return new NextResponse(null, { status: 413 });
  let body: unknown = null;
  try {
    body = JSON.parse(raw);
  } catch {
    return new NextResponse(null, { status: 400 });
  }
  const line = authTelemetryLogLine(body, "merchant", request.headers.get("user-agent"));
  if (!line) return new NextResponse(null, { status: 400 });
  console.warn(line);
  return new NextResponse(null, { status: 204 });
}
