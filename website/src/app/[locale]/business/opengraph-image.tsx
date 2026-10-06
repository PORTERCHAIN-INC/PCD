import { ogImageResponse } from "@/lib/seo/og-image";

export const alt = "PorterChain for business — transportation capacity";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function BusinessOpenGraphImage() {
  return ogImageResponse({
    eyebrow: "Business",
    title: "Capacity when your fleet cannot cover it",
    subtitle: "Same-day, overflow, and recurring vehicle-and-driver programs across the GTA",
    tone: "blue",
  });
}
