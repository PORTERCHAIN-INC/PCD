import { industrySlug, serviceAreaSlug, business, platform, serviceAreas } from "../routes";

export type CapabilitySection = {
  heading: string;
  body: string;
};

export type CapabilityPage = {
  slug: string;
  title: string;
  description: string;
  intro: string;
  sections: CapabilitySection[];
  industrySlugs: string[];
  serviceAreaSlugs: string[];
  relatedClusterSlugs?: string[];
  extraLinks?: {
    path: "onboarding" | "platform" | "serviceAreas" | "trustClaims";
    label: string;
  }[];
};

export type CapabilityLink = { href: string; label: string };
