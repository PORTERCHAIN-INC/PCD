import { ogImageResponse } from "@/lib/seo/og-image";

export const runtime = "edge";
export const alt = "PorterChain vehicle partner — join the capacity network";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function VehiclePartnerOpenGraphImage() {
  return ogImageResponse({
    eyebrow: "Vehicle partners",
    title: "Drive with PorterChain",
    subtitle: "Professional capacity partners for GTA and Ontario merchants",
    tone: "blue",
  });
}
