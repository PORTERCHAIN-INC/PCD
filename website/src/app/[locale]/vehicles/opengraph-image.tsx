import { ogImageResponse } from "@/lib/seo/og-image";

export const runtime = "edge";
export const alt = "PorterChain vehicles";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function VehiclesOpenGraphImage() {
  return ogImageResponse({
    eyebrow: "Vehicles",
    title: "Sedan to box truck — with a driver",
    subtitle: "Vehicle-and-driver capacity classes for same-day and recurring GTA lanes",
    tone: "slate",
  });
}
