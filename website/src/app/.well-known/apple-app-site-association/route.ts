import { buildAppleAppSiteAssociationDocument } from "@/lib/mobile-deep-links";

export async function GET() {
  const teamId = (process.env.APPLE_TEAM_ID ?? "TEAMID").trim();
  const body = buildAppleAppSiteAssociationDocument(teamId);

  return new Response(JSON.stringify(body), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
