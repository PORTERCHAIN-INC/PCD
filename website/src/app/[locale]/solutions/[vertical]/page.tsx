import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
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
  const index = cardIndexForVertical(vertical);
  const industry = industrySlugForVertical(vertical);

  return (
    <CorporateShell>
      <HeroSection
        badge={t("hero.badge")}
        title={t(`cards.items.${index}.title`)}
        subtitle={t(`cards.items.${index}.description`)}
        primaryCta={t("hero.primaryCta")}
        primaryHref="/contact"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/platform"
        variant="minimal"
      />
      <section className="site-section bg-gray-bg">
        <Container className="max-w-3xl text-center">
          <p className="text-muted leading-relaxed">
            {loc === "fr"
              ? "Porterchain adapte la planification, le dispatch et la visibilité en direct aux contraintes de votre secteur — avec des preuves de livraison prêtes pour l'audit."
              : "Porterchain adapts planning, dispatch, and live visibility to your sector's constraints — with audit-ready proof of delivery."}
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <LinkButton href={industrySlug(loc, industry)} showArrow>
              {loc === "fr" ? "Voir l'industrie" : "Explore industry playbook"}
            </LinkButton>
            <LinkButton href="/platform" variant="outline">
              {loc === "fr" ? "Voir la plateforme" : "View platform"}
            </LinkButton>
          </div>
        </Container>
      </section>
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="/contact"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/platform"
        variant="gradient"
      />
    </CorporateShell>
  );
}
