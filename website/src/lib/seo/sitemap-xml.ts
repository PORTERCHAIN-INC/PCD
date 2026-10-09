import type { MetadataRoute } from "next";
import { siteConfig } from "@/lib/seo/config";
import {
  SITEMAP_PARTITION_IDS,
  buildSitemapPartition,
  type SitemapPartitionId,
} from "@/lib/seo/sitemap-entries";

/**
 * Sitemaps are served by route handlers (not app/sitemap.ts) so that BOTH the index at
 * /sitemap.xml and the partitions at /sitemap/{id}.xml exist. Next's generateSitemaps()
 * only emits the partitions, and a metadata sitemap cannot coexist with a /sitemap.xml
 * route — production returned 404 for the index referenced by robots.txt.
 */

const XML_HEADERS = {
  "Content-Type": "application/xml; charset=utf-8",
  "Cache-Control": "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800",
} as const;

function esc(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function siteBase(): string {
  return siteConfig.baseUrl.replace(/\/$/, "");
}

export function isSitemapPartitionId(value: string): value is SitemapPartitionId {
  return (SITEMAP_PARTITION_IDS as string[]).includes(value);
}

export function sitemapIndexXml(): string {
  const base = siteBase();
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...SITEMAP_PARTITION_IDS.map(
      (id) => `<sitemap><loc>${esc(`${base}/sitemap/${id}.xml`)}</loc></sitemap>`
    ),
    "</sitemapindex>",
    "",
  ].join("\n");
}

export function urlsetXml(entries: MetadataRoute.Sitemap): string {
  const rows = entries.map((e) => {
    const parts = [`<loc>${esc(e.url)}</loc>`];
    if (e.lastModified) {
      const d = e.lastModified instanceof Date ? e.lastModified : new Date(e.lastModified);
      if (!Number.isNaN(d.getTime())) parts.push(`<lastmod>${d.toISOString()}</lastmod>`);
    }
    if (e.changeFrequency) parts.push(`<changefreq>${e.changeFrequency}</changefreq>`);
    if (typeof e.priority === "number") parts.push(`<priority>${e.priority}</priority>`);
    return `<url>${parts.join("")}</url>`;
  });
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...rows,
    "</urlset>",
    "",
  ].join("\n");
}

export async function sitemapPartitionXml(id: SitemapPartitionId): Promise<string> {
  "use cache";
  const result = buildSitemapPartition(id);
  return urlsetXml(result instanceof Promise ? await result : result);
}

export function xmlResponse(body: string, status = 200): Response {
  return new Response(body, { status, headers: XML_HEADERS });
}
