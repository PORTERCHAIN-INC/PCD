import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import CtaSection from "@/components/corporate/sections/CtaSection";
import HeroSection from "@/components/corporate/sections/HeroSection";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import { routing, type Locale } from "@/i18n/routing";
import {
  SOLUTION_VERTICAL_SLUGS,
  cardIndexForVertical,
  industrySlugForVertical,
  isValidSolutionVertical,
} from "@/lib/solutions-verticals";
import { industrySlug } from "@/lib/seo/routes";

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
  const t = await getTranslations({ locale, namespace: "corporate.solutions" });
  const index = cardIndexForVertical(vertical);
  return {
    title: `${t(`cards.items.${index}.title`)} | Porterchain Solutions`,
    description: t(`cards.items.${index}.description`),
  };
}

export default async function SolutionVerticalPage({ params }: Props) {
  const { locale, vertical } = await params;
  setRequestLocale(locale);
  if (!isValidSolutionVertical(vertical)) notFound();

  const loc = locale as Locale;
  const t = await getTranslations("corporate.solutions");
  const tBc = await getTranslations("corporate.breadcrumbs");
  const index = cardIndexForVertical(vertical);
  const industry = industrySlugForVertical(vertical);

  return (
    <CorporateShell>
      <PageBreadcrumbs
        items={[
          { label: tBc("home"), href: "/" },
          { label: tBc("solutions"), href: "/solutions" },
          { label: t(`cards.items.${index}.title`) },
        ]}
      />
      <HeroSection
        badge={t("hero.badge")}
        title={t(`cards.items.${index}.title`)}
        subtitle={t(`cards.items.${index}.description`)}
        primaryCta={t("hero.primaryCta")}
        primaryHref="/contact?intent=quote&from=solutions"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/business#fleet"
        variant="minimal"
      />
      <section className="site-section bg-gray-bg">
        <Container className="max-w-3xl text-center">
          <p className="text-muted leading-relaxed">{t("verticalDetail.body")}</p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <LinkButton href={industrySlug(loc, industry)} showArrow>
              {t("verticalDetail.exploreIndustry")}
            </LinkButton>
            <LinkButton href="/platform" variant="outline">
              {t("verticalDetail.viewPlatform")}
            </LinkButton>
            <LinkButton href="/customers" variant="outline">
              {t("verticalDetail.viewCustomers")}
            </LinkButton>
          </div>
        </Container>
      </section>
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="/contact?intent=quote&from=solutions"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/business#fleet"
        variant="gradient"
      />
    </CorporateShell>
  );
}
