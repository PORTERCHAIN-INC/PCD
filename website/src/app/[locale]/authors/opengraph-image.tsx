import { ogImageResponse } from "@/lib/seo/og-image";

export const runtime = "edge";
export const alt = "PorterChain blog authors";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function AuthorsOpenGraphImage() {
  return ogImageResponse({
    eyebrow: "Authors",
    title: "Operators writing for operators",
    subtitle: "Dispatch, capacity, and proof — from the people who run GTA lanes",
    tone: "slate",
  });
}
