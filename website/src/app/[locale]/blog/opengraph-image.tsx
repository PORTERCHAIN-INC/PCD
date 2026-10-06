import { ogImageResponse } from "@/lib/seo/og-image";

export const alt = "PorterChain blog — logistics capacity insights";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function BlogOpenGraphImage() {
  return ogImageResponse({
    eyebrow: "Blog",
    title: "Capacity, lanes, and local logistics",
    subtitle: "Insights for Ontario merchants running same-day and recurring delivery",
    tone: "slate",
  });
}
