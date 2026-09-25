import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { CAPABILITY_PAGES } from "@/lib/seo/content/capabilities";
import {
  getLocalizedCapability,
  getProgrammaticHubCopy,
  listLocalizedCapabilitySlugs,
} from "@/lib/seo/programmatic-content";
import { localeStaticParams, buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import { capabilitySlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

const EN_HUB = {
  title: "Capacity capabilities",
  description:
    "How PorterChain runs multi-stop, recurring, tracking, recovery, matching, and proof — full-stack capacity for GTA businesses.",
};

const EN_META = {
  title: "Capacity Capabilities | Multi-Stop, Tracking & Proof | PorterChain",
  description:
    "Explore PorterChain capabilities: multi-stop delivery, recurring routes, customer tracking, exception recovery, intelligent matching, and delivery verification for Ontario B2B lanes.",
};

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const hub = await getProgrammaticHubCopy(locale as Locale, "capabilities", EN_META);
  return buildProgrammaticPageMetadata(
    locale,
    "capabilities",
    hub.title,
    hub.description,
    locale === "fr"
  );
}

export default async function CapabilitiesHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;
  const slugs = new Set(await listLocalizedCapabilitySlugs(loc));
  const hub = await getProgrammaticHubCopy(loc, "capabilities", EN_HUB);

  const pages = CAPABILITY_PAGES.filter((p) => slugs.has(p.slug));
  const items = await Promise.all(
    pages.map(async (p) => {
      const page = (await getLocalizedCapability(loc, p.slug))!;
      return {
        href: capabilitySlug(loc, p.slug),
        title: page.title,
        description: page.description,
      };
    })
  );

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title={hub.title}
        description={hub.description}
        items={items}
        ctaSource="capabilities"
      />
    </CorporateShell>
  );
}
