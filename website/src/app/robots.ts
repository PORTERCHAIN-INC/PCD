import type { MetadataRoute } from "next";
import { siteConfig } from "@/lib/seo/config";
import { SITEMAP_PARTITION_IDS } from "@/lib/seo/sitemap-entries";

export default function robots(): MetadataRoute.Robots {
  const base = siteConfig.baseUrl.replace(/\/$/, "");
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/*/login", "/*/book", "/*/book/", "/*/track/"],
      },
    ],
    sitemap: [
      `${base}/sitemap.xml`,
      ...SITEMAP_PARTITION_IDS.map((id) => `${base}/sitemap/${id}.xml`),
    ],
  };
}
