import { ogImageResponse } from "@/lib/seo/og-image";

export const alt = "PorterChain — B2B transportation capacity in the GTA and Ontario";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return ogImageResponse({
    title: "B2B transportation capacity — GTA & Ontario",
    subtitle: "Vehicle + driver capacity · tracking · proof of delivery",
    tone: "navy",
  });
}
