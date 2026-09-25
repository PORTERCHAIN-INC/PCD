import { ogImageResponse } from "@/lib/seo/og-image";

export const runtime = "edge";
export const alt = "PorterChain trust — insurance, SLA, and security";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function TrustOpenGraphImage() {
  return ogImageResponse({
    eyebrow: "Trust",
    title: "Insurance, SLA, and delivery standards",
    subtitle: "Documents and commitments for procurement and ops partners",
    tone: "slate",
  });
}
