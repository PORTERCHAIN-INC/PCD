import { SITEMAP_PARTITION_IDS } from "@/lib/seo/sitemap-entries";
import { isSitemapPartitionId, sitemapPartitionXml, xmlResponse } from "@/lib/seo/sitemap-xml";

/** /sitemap/{partition}.xml — one urlset per content partition (static, delivery, …). */
export function generateStaticParams() {
  return SITEMAP_PARTITION_IDS.map((id) => ({ id: `${id}.xml` }));
}

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const raw = (await ctx.params).id;
  const id = raw.endsWith(".xml") ? raw.slice(0, -4) : raw;
  if (!isSitemapPartitionId(id)) {
    return xmlResponse('<?xml version="1.0" encoding="UTF-8"?><error>not found</error>', 404);
  }
  return xmlResponse(await sitemapPartitionXml(id));
}
