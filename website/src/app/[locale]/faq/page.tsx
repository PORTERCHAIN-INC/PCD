import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { AUTHORITY_PAGES } from "@/lib/seo/content/authority-pages";
import { FAQ_CLUSTERS } from "@/lib/seo/content/faq-clusters";
import { INTEGRATIONS_EDUCATION_PAGES } from "@/lib/seo/content/integrations-education";
import { ONBOARDING_EDUCATION_PAGES } from "@/lib/seo/content/onboarding-education";
import {
  getLocalizedAuthorityPage,
  getLocalizedFaqCluster,
  getProgrammaticHubCopy,
  listLocalizedFaqSlugs,
  listLocalizedGuideSlugs,
} from "@/lib/seo/programmatic-content";
import { localeStaticParams, buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import {
  faqSlug,
  guideSlug,
  integrationsEducationSlug,
  localePath,
  onboardingEducationSlug,
} from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

const EN_HUB = {
  title: "FAQ & guides",
  description:
    "Answers about pricing, onboarding, capacity, and service areas — plus practical guides on how PorterChain works for GTA merchants.",
};

const EN_META = {
  title: "FAQ & guides for merchants | Porterchain",
  description:
    "Frequently asked questions and practical guides covering pricing, onboarding, tracking, APIs, industries, and local delivery across the GTA.",
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
  const faqSlugs = new Set(await listLocalizedFaqSlugs(loc));
  const guideSlugs = new Set(await listLocalizedGuideSlugs(loc));
  const hub = await getProgrammaticHubCopy(loc, "faq", EN_HUB);

  const faqItems = await Promise.all(
    FAQ_CLUSTERS.filter((c) => faqSlugs.has(c.slug)).map(async (c) => {
      const cluster = (await getLocalizedFaqCluster(loc, c.slug))!;
      return {
        href: faqSlug(loc, c.slug),
        title: cluster.title,
        description: cluster.description,
      };
    })
  );

  const authorityPages = AUTHORITY_PAGES.filter((p) =>
    p.slug === "how-porterchain-works" ? loc === "en" : guideSlugs.has(p.slug)
  );
  const guideItems = await Promise.all(
    authorityPages.map(async (p) => {
      const page = (await getLocalizedAuthorityPage(loc, p.slug))!;
      return {
        href:
          p.slug === "how-porterchain-works"
            ? localePath(loc, "how-porterchain-works")
            : guideSlug(loc, p.slug),
        title: page.title,
        description: page.description,
      };
    })
  );

  const educationItems =
    loc === "en"
      ? [
          ...ONBOARDING_EDUCATION_PAGES.map((p) => ({
            href: onboardingEducationSlug(loc, p.slug),
            title: p.title,
            description: p.description,
          })),
          ...INTEGRATIONS_EDUCATION_PAGES.map((p) => ({
            href: integrationsEducationSlug(loc, p.slug),
            title: p.title,
            description: p.description,
          })),
        ]
      : [];

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title={hub.title}
        description={hub.description}
        items={[...faqItems, ...guideItems, ...educationItems]}
        ctaSource="faq"
      />
    </CorporateShell>
  );
}
