import { ogImageResponse } from "@/lib/seo/og-image";

export const runtime = "edge";
export const alt = "PorterChain careers";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function CareersOpenGraphImage() {
  return ogImageResponse({
    eyebrow: "Careers",
    title: "Build the capacity network",
    subtitle: "Ops, engineering, and field roles for people who move commerce in the GTA",
    tone: "blue",
  });
}
