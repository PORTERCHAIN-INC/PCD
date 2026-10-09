import { NextResponse } from "next/server";
import { getPorterchainApiBase } from "@/lib/api-base";

const OFF = {
  hero_ab: { enabled: false, experiment: "hero_copy_v1", split_percent: 0 },
  calculator: { enabled: true },
};

/** Website switches (hero A/B flag). Falls back to "everything off" if the API is down. */
export async function GET() {
  try {
    const res = await fetch(`${getPorterchainApiBase()}/v1/public/marketing-config`, {
      cache: "no-store",
    });
    const data = res.ok ? await res.json() : OFF;
    return NextResponse.json(data, {
      headers: { "Cache-Control": "public, max-age=60, stale-while-revalidate=300" },
    });
  } catch {
    return NextResponse.json(OFF, { headers: { "Cache-Control": "public, max-age=30" } });
  }
}
