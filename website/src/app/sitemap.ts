import type { MetadataRoute } from "next";
import { cacheLife } from "next/cache";
import {
  SITEMAP_PARTITION_IDS,
  buildSitemapPartition,
  type SitemapPartitionId,
} from "@/lib/seo/sitemap-entries";

export async function generateSitemaps() {
  return SITEMAP_PARTITION_IDS.map((id) => ({ id }));
}

export default async function sitemap(props: {
  id: Promise<SitemapPartitionId>;
}): Promise<MetadataRoute.Sitemap> {
  "use cache";
  cacheLife("days");
  const id = await props.id;
  const result = buildSitemapPartition(id);
  return result instanceof Promise ? await result : result;
}
