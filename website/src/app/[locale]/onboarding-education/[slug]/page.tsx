import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import {
  ONBOARDING_EDUCATION_PAGES,
  getOnboardingEducationBySlug,
  buildOnboardingEducationInternalLinks,
} from "@/lib/seo/content/onboarding-education";
import { onboardingEducationSlug } from "@/lib/seo/routes";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    for (const page of ONBOARDING_EDUCATION_PAGES) {
      params.push({ locale, slug: page.slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const page = getOnboardingEducationBySlug(slug);
  if (!page) return {};
  return buildPageMetadata(locale, `onboarding-education/${slug}`, page.title, page.description, {
    index: locale === "en",
  });
}

export default async function OnboardingEducationPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const page = getOnboardingEducationBySlug(slug);
  if (!page) notFound();

  const loc = locale as Locale;
  const links = buildOnboardingEducationInternalLinks(loc, page, onboardingEducationSlug);

  return (
    <CorporateShell>
      <ContentClusterView
        locale={loc}
        ctaSource={`onboarding-education/${slug}`}
        data={{
          title: page.title,
          description: page.description,
          intro: page.intro,
          sections: page.sections,
          relatedLinks: [
            ...links.industry,
            ...links.serviceAreas,
            ...links.extra,
            ...links.cluster,
          ],
        }}
      />
    </CorporateShell>
  );
}
