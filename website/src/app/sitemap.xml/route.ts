import { sitemapIndexXml, xmlResponse } from "@/lib/seo/sitemap-xml";

/** /sitemap.xml — sitemap index listing every /sitemap/{id}.xml partition. */
export function GET() {
  return xmlResponse(sitemapIndexXml());
}
