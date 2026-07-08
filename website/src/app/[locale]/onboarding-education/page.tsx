import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { ONBOARDING_EDUCATION_PAGES } from "@/lib/seo/content/onboarding-education";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { onboardingEducationSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "onboarding-education",
    "Merchant onboarding education | Porterchain",
    "Guides on getting started, order data, CSV uploads, API onboarding, and first route expectations."
  );
}

export default async function OnboardingEducationHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title="Onboarding education"
        description="Everything you need to get merchant delivery live with Porterchain."
        items={ONBOARDING_EDUCATION_PAGES.map((p) => ({
          href: onboardingEducationSlug(loc, p.slug),
          title: p.title,
          description: p.description,
        }))}
        ctaSource="onboarding-education"
      />
    </CorporateShell>
  );
}
