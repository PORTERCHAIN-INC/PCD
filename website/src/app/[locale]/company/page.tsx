import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HeroSection from "@/components/corporate/sections/HeroSection";
import TimelineSection from "@/components/corporate/sections/TimelineSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import { RelatedResourcesSection } from "@/components/corporate/sections/CardGridSection";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import {
  collectFaqItems,
  collectResourceItems,
  collectTimelineSteps,
} from "@/lib/corporate-content";
import { Shield, Scale, Leaf, Handshake } from "lucide-react";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.company" });
  return {
    title: t("title"),
    description: t("description"),
    openGraph: { title: t("ogTitle"), description: t("ogDescription") },
  };
}

export default async function CompanyPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.company");

  const missionItems = [
    { title: t("mission.items.0.title"), description: t("mission.items.0.description") },
    { title: t("mission.items.1.title"), description: t("mission.items.1.description") },
    { title: t("mission.items.2.title"), description: t("mission.items.2.description") },
  ];

  const valueItems = [
    {
      title: t("values.items.0.title"),
      description: t("values.items.0.description"),
      icon: Shield,
    },
    { title: t("values.items.1.title"), description: t("values.items.1.description"), icon: Scale },
    { title: t("values.items.2.title"), description: t("values.items.2.description"), icon: Leaf },
    {
      title: t("values.items.3.title"),
      description: t("values.items.3.description"),
      icon: Handshake,
    },
  ];

  return (
    <CorporateShell>
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="/contact"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/careers"
        variant="minimal"
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
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="/contact"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/contact"
        variant="gradient"
      />
      <FaqSection
        label={t("faq.label")}
        title={t("faq.title")}
        items={collectFaqItems(t, "faq.items", 4)}
      />
      <RelatedResourcesSection
        label={t("resources.label")}
        title={t("resources.title")}
        items={collectResourceItems(t, "resources.items", 3)}
      />
    </CorporateShell>
  );
}
