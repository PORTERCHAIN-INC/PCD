import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { FAQ_CLUSTERS } from "@/lib/seo/content/faq-clusters";
import {
  getLocalizedFaqCluster,
  getProgrammaticHubCopy,
  listLocalizedFaqSlugs,
} from "@/lib/seo/programmatic-content";
import { localeStaticParams, buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import { faqSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

const EN_HUB = {
  title: "Frequently asked questions",
  description:
    "Practical answers about merchant delivery, pricing, onboarding, and local service areas across the GTA and Ontario.",
};

const EN_META = {
  title: "Delivery FAQ for merchants | Porterchain",
  description:
    "Answers about pricing, onboarding, CSV uploads, API integrations, service areas, and industry-specific delivery.",
};

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const hub = await getProgrammaticHubCopy(locale as Locale, "faq", EN_META);
  return buildProgrammaticPageMetadata(locale, "faq", hub.title, hub.description, locale === "fr");
}

export default async function FaqHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;
  const slugs = new Set(await listLocalizedFaqSlugs(loc));
  const hub = await getProgrammaticHubCopy(loc, "faq", EN_HUB);

  const clusters = FAQ_CLUSTERS.filter((c) => slugs.has(c.slug));
  const items = await Promise.all(
    clusters.map(async (c) => {
      const cluster = (await getLocalizedFaqCluster(loc, c.slug))!;
      return {
        href: faqSlug(loc, c.slug),
        title: cluster.title,
        description: cluster.description,
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
        ctaSource="faq"
      />
    </CorporateShell>
  );
}
