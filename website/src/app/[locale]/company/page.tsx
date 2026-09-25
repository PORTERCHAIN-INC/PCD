import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import MarketingHero from "@/components/marketing/MarketingHero";
import BrandMergeBand from "@/components/marketing/brand/BrandMergeBand";
import TimelineSection from "@/components/marketing/corporate/sections/TimelineSection";
import FeatureSection from "@/components/marketing/corporate/sections/FeatureSection";
import MarketingCloser from "@/components/marketing/MarketingCloser";
import MarketingFaq from "@/components/marketing/MarketingFaq";
import { RelatedResourcesSection } from "@/components/marketing/corporate/sections/CardGridSection";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/marketing/corporate/motion/FadeIn";
import {
  collectFaqItems,
  collectResourceItems,
  collectTimelineSteps,
} from "@/lib/corporate-content";
import { siteImages } from "@/data/site-images";
import { JsonLd } from "@/components/seo";
import { buildCorporationSchema, buildOrganizationSchema } from "@/lib/seo/schema";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.company" });
  return buildPageMetadata(locale, "company", t("title"), t("description"));
}

export default async function CompanyPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.company");
  const tCta = await getTranslations("common.cta");
  const tBc = await getTranslations("corporate.breadcrumbs");

  const missionItems = [
    { title: t("mission.items.0.title"), description: t("mission.items.0.description") },
    { title: t("mission.items.1.title"), description: t("mission.items.1.description") },
    { title: t("mission.items.2.title"), description: t("mission.items.2.description") },
  ];

  const valueItems = [
    {
      title: t("values.items.0.title"),
      description: t("values.items.0.description"),
      icon: "shield" as const,
    },
    {
      title: t("values.items.1.title"),
      description: t("values.items.1.description"),
      icon: "scale" as const,
    },
    {
      title: t("values.items.2.title"),
      description: t("values.items.2.description"),
      icon: "leaf" as const,
    },
    {
      title: t("values.items.3.title"),
      description: t("values.items.3.description"),
      icon: "handshake" as const,
    },
  ];

  return (
    <CorporateShell>
      <JsonLd data={[buildOrganizationSchema(), buildCorporationSchema()]} />
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: t("hero.badge") }]} />
      <MarketingHero
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={tCta("quote")}
        primaryHref="/sign-up?intent=quote&from=company"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/careers"
        variant="minimal"
      />
      <BrandMergeBand
        eyebrow={t("brandBand.eyebrow")}
        title={t("brandBand.title")}
        body={t("brandBand.body")}
        imageSide="left"
        image={siteImages.brand.depot}
        objectPosition="center 40%"
      />
      <section className="site-section bg-gray-bg">
        <Container>
          <SectionHeader label={t("mission.label")} title={t("mission.title")} />
          <div className="grid md:grid-cols-3 gap-5">
            {missionItems.map((item, i) => (
              <FadeIn key={i} delay={i * 0.08}>
                <div className="card-surface p-7 h-full border-t-2 border-t-secondary">
                  <h3 className="text-lg font-semibold text-primary">{item.title}</h3>
                  <p className="mt-3 text-sm text-muted leading-relaxed">{item.description}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </Container>
      </section>
      <TimelineSection
        label={t("timeline.label")}
        title={t("timeline.title")}
        subtitle={t("timeline.subtitle")}
        steps={collectTimelineSteps(t, "timeline.steps", 4)}
        variant="horizontal"
        className="bg-white"
      />
      <FeatureSection
        label={t("values.label")}
        title={t("values.title")}
        items={valueItems}
        variant="grid"
      />
      <MarketingCloser
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={tCta("quote")}
        primaryHref="/sign-up?intent=quote&from=company"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/vehicle-partner"
        variant="gradient"
      />
      <MarketingFaq
        label={t("faq.label")}
        title={t("faq.title")}
        items={collectFaqItems(t, "faq.items", 5)}
      />
      <RelatedResourcesSection
        label={t("resources.label")}
        title={t("resources.title")}
        items={collectResourceItems(t, "resources.items", 3)}
      />
    </CorporateShell>
  );
}
