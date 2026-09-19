import { NextResponse } from "next/server";
import { publicEnv } from "@/lib/env";

/** Simple blog RSS for distribution / monitoring tools. */
export async function GET() {
  const base = publicEnv.siteUrl.replace(/\/$/, "");
  const items = [
    {
      title: "Porterchain capacity network",
      link: `${base}/en/blog`,
      description: "Articles and operational insights from Porterchain.",
    },
  ];

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Porterchain Blog</title>
    <link>${base}/en/blog</link>
    <description>Porterchain B2B transportation capacity insights</description>
    ${items
      .map(
        (item) => `<item>
      <title>${escapeXml(item.title)}</title>
      <link>${escapeXml(item.link)}</link>
      <description>${escapeXml(item.description)}</description>
      <guid>${escapeXml(item.link)}</guid>
    </item>`
      )
      .join("\n")}
  </channel>
</rss>`;

  return new NextResponse(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
