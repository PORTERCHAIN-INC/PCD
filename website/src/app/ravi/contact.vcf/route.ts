import { buildRaviVCard, raviVCardFilename } from "@/lib/ravi-vcard";

export function GET() {
  const body = buildRaviVCard();
  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": "text/vcard; charset=utf-8",
      "Content-Disposition": `attachment; filename="${raviVCardFilename}"`,
      "Cache-Control": "public, max-age=3600",
    },
  });
}
