import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HeroSection from "@/components/corporate/sections/HeroSection";
import SolutionVerticalHub from "@/components/solutions/SolutionVerticalHub";
import { routing, type Locale } from "@/i18n/routing";
import {
  SOLUTION_VERTICAL_SLUGS,
  isValidSolutionVertical,
  type SolutionVerticalSlug,
} from "@/lib/solutions-verticals";
import { SOLUTION_MESSAGE_KEYS } from "@/lib/solutions-hub-config";
import { buildPageMetadata } from "@/lib/seo/page-helpers";

type Props = { params: Promise<{ locale: string; vertical: string }> };

export function generateStaticParams() {
  const params: { locale: string; vertical: string }[] = [];
  for (const locale of routing.locales) {
    for (const vertical of SOLUTION_VERTICAL_SLUGS) {
      params.push({ locale, vertical });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, vertical } = await params;
  if (!isValidSolutionVertical(vertical)) return {};
  const messageKey = SOLUTION_MESSAGE_KEYS[vertical];
  const t = await getTranslations({ locale, namespace: `corporate.solutions.${messageKey}` });
  return buildPageMetadata(locale, `solutions/${vertical}`, t("meta.title"), t("meta.description"));
}

const SECONDARY_INDUSTRY: Partial<Record<SolutionVerticalSlug, string>> = {
  construction: "construction-materials",
};

function secondaryHrefForVertical(vertical: SolutionVerticalSlug): string {
  const industryPath = SECONDARY_INDUSTRY[vertical];
  if (industryPath) return `/industry/${industryPath}`;
  return "/industry";
}

export default async function SolutionVerticalPage({ params }: Props) {
  const { locale, vertical } = await params;
  setRequestLocale(locale);
  if (!isValidSolutionVertical(vertical)) notFound();

  const messageKey = SOLUTION_MESSAGE_KEYS[vertical];
  const t = await getTranslations(`corporate.solutions.${messageKey}`);
  const tBc = await getTranslations("corporate.breadcrumbs");
  const secondaryHref = secondaryHrefForVertical(vertical);

  return (
    <CorporateShell>
      <PageBreadcrumbs
        items={[
          { label: tBc("home"), href: "/" },
          { label: tBc("solutions"), href: "/solutions" },
          { label: t("breadcrumb") },
        ]}
      />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref={`/contact?intent=quote&from=solutions-${vertical}`}
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref={secondaryHref}
        variant="light-centered"
        trackSource={`solutions/${vertical}`}
      />
      <SolutionVerticalHub vertical={vertical} />
    </CorporateShell>
  );
}
