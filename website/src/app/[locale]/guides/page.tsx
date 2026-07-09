import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HubIndexView from "@/components/seo/HubIndexView";
import { AUTHORITY_PAGES } from "@/lib/seo/content/authority-pages";
import { ONBOARDING_EDUCATION_PAGES } from "@/lib/seo/content/onboarding-education";
import { INTEGRATIONS_EDUCATION_PAGES } from "@/lib/seo/content/integrations-education";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { guideSlug, onboardingEducationSlug, integrationsEducationSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "guides",
    "Local delivery guides | Porterchain",
    "Practical guides on how Porterchain works, onboarding, tracking, and support for GTA merchants."
  );
}

export default async function GuidesHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;
  const tBc = await getTranslations("corporate.breadcrumbs");

  const items = [
    ...AUTHORITY_PAGES.map((p) => ({
      href: guideSlug(loc, p.slug),
      title: p.title,
      description: p.description,
    })),
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
  ];

  return (
    <CorporateShell>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: tBc("guides") }]} />
      <HubIndexView
        locale={loc}
        title="Guides"
        description="Educational guides that build trust and explain how Porterchain transportation capacity works for Ontario businesses."
        items={items}
        ctaSource="guides"
      />
    </CorporateShell>
  );
}
