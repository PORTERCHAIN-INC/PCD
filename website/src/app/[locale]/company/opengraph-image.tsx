import { ogImageResponse } from "@/lib/seo/og-image";

export const alt = "PorterChain company — transportation capacity network";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function CompanyOpenGraphImage() {
  return ogImageResponse({
    eyebrow: "Company",
    title: "Built for GTA businesses that move",
    subtitle: "Transportation capacity network — vehicles, drivers, and ops software as one system",
    tone: "navy",
  });
}
