import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const ACCESS_COOKIE = "driver_access_token";

export async function GET() {
  const jar = await cookies();
  const token = jar.get(ACCESS_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }
  return NextResponse.json({ token });
}
