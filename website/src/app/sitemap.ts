import type { MetadataRoute } from "next";
import { buildSitemap } from "@/lib/seo/sitemap-entries";

/** Pre-render at build time so crawlers get a stable XML document (GSC-friendly). */
export const dynamic = "force-static";
export const revalidate = 86_400;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  return buildSitemap();
}
