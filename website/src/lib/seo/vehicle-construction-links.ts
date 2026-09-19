import type { Locale } from "@/i18n/routing";
import { INDUSTRY_PAGE_LABELS } from "./internal-linking";
import { industrySlug } from "./routes";

const VEHICLE_INDUSTRY_SLUGS: Record<string, string[]> = {
  van: ["construction-materials", "plumbing-supply"],
  mediumTruck: ["construction-materials", "electrical-distribution"],
};

export function buildVehicleConstructionLinks(
  locale: Locale,
  messageKey: string
): { href: string; label: string }[] {
  const slugs = VEHICLE_INDUSTRY_SLUGS[messageKey];
  if (!slugs) return [];

  return slugs.map((slug) => ({
    href: industrySlug(locale, slug),
    label: `${INDUSTRY_PAGE_LABELS[slug] ?? slug} delivery`,
  }));
}
