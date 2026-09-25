import { ogImageResponse } from "@/lib/seo/og-image";

export const runtime = "edge";
export const alt = "PorterChain solutions";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function SolutionsOpenGraphImage() {
  return ogImageResponse({
    eyebrow: "Solutions",
    title: "Capacity by industry and use case",
    subtitle: "Wholesale, medical, construction, food, 3PL, and fleet overflow across the GTA",
    tone: "blue",
  });
}
