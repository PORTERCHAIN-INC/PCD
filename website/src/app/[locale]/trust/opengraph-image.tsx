import { ogImageResponse } from "@/lib/seo/og-image";

export const alt = "PorterChain trust: coverage, proof of delivery and privacy";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function TrustOpenGraphImage() {
  return ogImageResponse({
    eyebrow: "Trust",
    title: "$2,500 coverage, photo proof, clear claims",
    subtitle: "Documents and commitments for procurement and ops partners",
    tone: "slate",
  });
}
