import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HubIndexView from "@/components/seo/HubIndexView";
import { AUTHORITY_PAGES } from "@/lib/seo/content/authority-pages";
import { ONBOARDING_EDUCATION_PAGES } from "@/lib/seo/content/onboarding-education";
import { INTEGRATIONS_EDUCATION_PAGES } from "@/lib/seo/content/integrations-education";
import {
  getLocalizedAuthorityPage,
  getProgrammaticHubCopy,
  listLocalizedGuideSlugs,
} from "@/lib/seo/programmatic-content";
import { localeStaticParams, buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import {
  guideSlug,
  integrationsEducationSlug,
  localePath,
  onboardingEducationSlug,
} from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

const EN_HUB = {
  title: "Guides",
  description:
    "Educational guides that build trust and explain how Porterchain transportation capacity works for Ontario businesses.",
};

const EN_META = {
  title: "Local delivery guides | Porterchain",
  description:
    "Practical guides on how Porterchain works, onboarding, tracking, and support for GTA merchants.",
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
  const tBc = await getTranslations("corporate.breadcrumbs");
  const hub = await getProgrammaticHubCopy(loc, "guides", EN_HUB);
  const guideSlugs = new Set(await listLocalizedGuideSlugs(loc));

  const authorityPages = AUTHORITY_PAGES.filter((p) =>
    p.slug === "how-porterchain-works" ? loc === "en" : guideSlugs.has(p.slug)
  );
  const authorityItems = await Promise.all(
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

  const enOnlyItems =
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
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: tBc("guides") }]} />
      <HubIndexView
        locale={loc}
        title={hub.title}
        description={hub.description}
        items={[...authorityItems, ...enOnlyItems]}
        ctaSource="guides"
      />
    </CorporateShell>
  );
}
