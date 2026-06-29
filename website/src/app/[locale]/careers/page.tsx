import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import CareersHero from "@/components/corporate/sections/CareersHero";
import BenefitsSection from "@/components/corporate/sections/BenefitsSection";
import OpenPositionsSection from "@/components/corporate/sections/OpenPositionsSection";
import { buildPositionsFromTranslations } from "@/lib/careers-content";
import TimelineSection from "@/components/corporate/sections/TimelineSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import TestimonialsSection from "@/components/corporate/sections/TestimonialsSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CareersCtaSection from "@/components/corporate/sections/CareersCtaSection";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import { collectFaqItems, collectTimelineSteps } from "@/lib/corporate-content";
import type { CareerDepartment } from "@/data/careers";
import {
  Shield,
  Scale,
  Leaf,
  Handshake,
  Wifi,
  Clock,
  GraduationCap,
  Laptop,
  TrendingUp,
  Heart,
  CheckCircle2,
} from "lucide-react";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.careers" });
  return {
    title: t("title"),
    description: t("description"),
    openGraph: { title: t("ogTitle"), description: t("ogDescription") },
  };
}

export default async function CareersPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.careers");

  const departmentLabels = {
    operations: t("positions.departments.operations"),
    engineering: t("positions.departments.engineering"),
    sales: t("positions.departments.sales"),
    marketing: t("positions.departments.marketing"),
    customerSuccess: t("positions.departments.customerSuccess"),
    driverSuccess: t("positions.departments.driverSuccess"),
    dispatch: t("positions.departments.dispatch"),
  } satisfies Record<CareerDepartment, string>;

  const benefitIcons = [Wifi, Clock, GraduationCap, Laptop, TrendingUp, Heart];
  const benefitItems = benefitIcons.map((icon, i) => ({
    title: t(`benefits.items.${i}.title`),
    description: t(`benefits.items.${i}.description`),
    icon,
  }));

  const valueItems = [
    { title: t("values.items.0.title"), description: t("values.items.0.description"), icon: Shield },
    { title: t("values.items.1.title"), description: t("values.items.1.description"), icon: Scale },
    { title: t("values.items.2.title"), description: t("values.items.2.description"), icon: Leaf },
    { title: t("values.items.3.title"), description: t("values.items.3.description"), icon: Handshake },
  ];

  const testimonials = [0, 1, 2].map((i) => ({
    quote: t(`testimonials.items.${i}.quote`),
    name: t(`testimonials.items.${i}.name`),
    role: t(`testimonials.items.${i}.role`),
  }));

  const whyPoints = [0, 1, 2].map((i) => t(`why.points.${i}`));
  const cultureTraits = [0, 1, 2].map((i) => ({
    title: t(`culture.traits.${i}.title`),
    description: t(`culture.traits.${i}.description`),
  }));

  const tPositions = await getTranslations("corporate.careers.positions");
  const positions = buildPositionsFromTranslations((key) => tPositions(key));

  return (
    <CorporateShell>
      <CareersHero
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        secondaryCta={t("hero.secondaryCta")}
      />

      <section className="site-section bg-white">
        <Container>
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            <FadeIn>
              <span className="text-xs font-semibold uppercase tracking-wider text-secondary">
                {t("mission.label")}
              </span>
              <h2 className="mt-3 text-3xl sm:text-4xl font-semibold text-primary tracking-tight text-balance leading-[1.12]">
                {t("mission.title")}
              </h2>
              <p className="mt-5 text-muted leading-relaxed">{t("mission.description")}</p>
            </FadeIn>
            <FadeIn delay={0.1}>
              <div className="rounded-2xl bg-primary p-8 sm:p-10 relative overflow-hidden">
                <div className="absolute inset-0 dot-pattern opacity-20" aria-hidden />
                <span className="relative text-xs font-semibold uppercase tracking-wider text-secondary">
                  {t("why.label")}
                </span>
                <h3 className="relative mt-3 text-xl font-semibold text-white tracking-tight">
                  {t("why.title")}
                </h3>
                <p className="relative mt-3 text-sm text-white/60 leading-relaxed">{t("why.description")}</p>
                <ul className="relative mt-6 space-y-3">
                  {whyPoints.map((point, i) => (
                    <li key={i} className="flex gap-3 text-sm text-white/80">
                      <CheckCircle2 className="w-4 h-4 text-secondary shrink-0 mt-0.5" aria-hidden />
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            </FadeIn>
          </div>
        </Container>
      </section>

      <section className="site-section bg-gray-bg">
        <Container>
          <SectionHeader
            label={t("culture.label")}
            title={t("culture.title")}
            subtitle={t("culture.description")}
          />
          <div className="grid md:grid-cols-3 gap-5">
            {cultureTraits.map((trait, i) => (
              <FadeIn key={i} delay={i * 0.08}>
                <div className="card-surface p-7 h-full text-center md:text-left">
                  <div className="w-10 h-10 rounded-full bg-secondary/10 flex items-center justify-center mx-auto md:mx-0 mb-4">
                    <span className="text-sm font-bold text-secondary">{i + 1}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-primary">{trait.title}</h3>
                  <p className="mt-2 text-sm text-muted leading-relaxed">{trait.description}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </Container>
      </section>

      <FeatureSection
        label={t("values.label")}
        title={t("values.title")}
        items={valueItems}
        variant="pillars"
      />

      <BenefitsSection
        label={t("benefits.label")}
        title={t("benefits.title")}
        subtitle={t("benefits.subtitle")}
        items={benefitItems}
      />

      <OpenPositionsSection
        label={t("positions.label")}
        title={t("positions.title")}
        subtitle={t("positions.subtitle")}
        allLabel={t("positions.all")}
        departmentLabels={departmentLabels}
        positions={positions}
      />

      <TimelineSection
        label={t("hiringProcess.label")}
        title={t("hiringProcess.title")}
        subtitle={t("hiringProcess.subtitle")}
        steps={collectTimelineSteps(t, "hiringProcess.steps", 5)}
        variant="horizontal"
        className="bg-white"
      />

      <TestimonialsSection
        label={t("testimonials.label")}
        title={t("testimonials.title")}
        items={testimonials}
      />

      <FaqSection
        label={t("faq.label")}
        title={t("faq.title")}
        items={collectFaqItems(t, "faq.items", 5)}
        className="bg-gray-bg"
      />

      <CareersCtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        secondaryLabel={t("cta.secondary")}
      />
    </CorporateShell>
  );
}
