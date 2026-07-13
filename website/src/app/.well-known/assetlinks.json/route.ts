import { buildAndroidAssetLinks, parseFingerprintList } from "@/lib/mobile-deep-links";

export const dynamic = "force-static";

const PLACEHOLDER =
  "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00";

export async function GET() {
  const customer = parseFingerprintList(process.env.ANDROID_APP_LINK_SHA256_CUSTOMER, PLACEHOLDER);
  const driver = parseFingerprintList(process.env.ANDROID_APP_LINK_SHA256_DRIVER, PLACEHOLDER);
  const body = buildAndroidAssetLinks({ customer, driver });

  return new Response(JSON.stringify(body), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
