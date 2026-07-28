import type { MetadataRoute } from "next";
import { siteConfig } from "@/lib/seo/config";

export default function robots(): MetadataRoute.Robots {
  const base = siteConfig.baseUrl.replace(/\/$/, "");
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/*/login", "/*/book/continue", "/*/book/success", "/*/track/"],
      },
    ],
    sitemap: [
      `${base}/sitemap.xml`,
      ...[
        "static",
        "industry",
        "service",
        "vehicle",
        "location",
        "resource",
        "article",
        "case-study",
        "developer",
      ].map((id) => `${base}/sitemap/${id}.xml`),
    ],
  };
}
