import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { AUTHORITY_PAGES } from "@/lib/seo/content/authority-pages";
import {
  getLocalizedAuthorityPage,
  getProgrammaticHubCopy,
  listLocalizedGuideSlugs,
} from "@/lib/seo/programmatic-content";
import { localeStaticParams, buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import { guideSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

const EN_HUB = {
  title: "Local delivery guides",
  description:
    "Practical guides on transportation capacity, same-day GTA delivery, failure recovery, onboarding, and operations for Ontario businesses.",
};

const EN_META = {
  title: "Delivery Guides | Capacity, Same-Day & Ops | PorterChain",
  description:
    "PorterChain guides for GTA B2B delivery: transportation capacity networks, same-day capacity, failure modes, onboarding, tracking, and commercial courier evaluation.",
};

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const hub = await getProgrammaticHubCopy(locale as Locale, "guides", EN_META);
  return buildProgrammaticPageMetadata(
    locale,
    "guides",
    hub.title,
    hub.description,
    locale === "fr"
  );
}

export default async function GuidesHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;
  const slugs = new Set(await listLocalizedGuideSlugs(loc));
  const hub = await getProgrammaticHubCopy(loc, "guides", EN_HUB);

  const pages = AUTHORITY_PAGES.filter(
    (p) => p.slug !== "how-porterchain-works" && slugs.has(p.slug)
  );
  const items = await Promise.all(
    pages.map(async (p) => {
      const page = (await getLocalizedAuthorityPage(loc, p.slug))!;
      return {
        href: guideSlug(loc, p.slug),
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
        ctaSource="guides"
      />
    </CorporateShell>
  );
}
