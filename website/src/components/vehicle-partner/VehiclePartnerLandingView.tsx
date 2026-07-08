import { getTranslations } from "next-intl/server";
import { Car, Truck, Package, Box, CarFront } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import HeroSection from "@/components/corporate/sections/HeroSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import Container from "@/components/ui/Container";
import { JsonLd } from "@/components/seo";
import { buildFAQPageSchema } from "@/lib/seo/schema";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { siteImages, getVehiclePartnerImage } from "@/data/site-images";
import { driverPortalUrl } from "@/data/portal-links";
import type { Locale } from "@/i18n/routing";

const VEHICLE_KEYS = ["sedan", "suv", "pickup", "van", "boxTruck"] as const;
const VEHICLE_ICONS: Record<(typeof VEHICLE_KEYS)[number], LucideIcon> = {
  sedan: Car,
  suv: CarFront,
  pickup: Truck,
  van: Package,
  boxTruck: Box,
};

const PILLAR_KEYS = ["routes", "earnings", "support", "multiple"] as const;
const EASE_KEYS = ["clarity", "tools", "fleet", "local"] as const;
const WORKFLOW_KEYS = ["step1", "step2", "step3"] as const;

type Props = { locale: Locale };

export default async function VehiclePartnerLandingView({ locale }: Props) {
  const t = await getTranslations("vehiclePartner");

  const faqItems = t.raw("faq.items") as { question: string; answer: string }[];
  const contactHref = `/${locale}/contact`;

  const vehicleItems = VEHICLE_KEYS.map((key) => ({
    title: t(`vehicles.items.${key}.title`),
    description: t(`vehicles.items.${key}.description`),
    icon: VEHICLE_ICONS[key],
    image: getVehiclePartnerImage(key),
  }));

  const pillarItems = PILLAR_KEYS.map((key) => ({
    title: t(`pillars.items.${key}.title`),
    description: t(`pillars.items.${key}.description`),
  }));

  const easeItems = EASE_KEYS.map((key) => ({
    title: t(`ease.items.${key}.title`),
    description: t(`ease.items.${key}.description`),
    ...(key === "local" ? { image: siteImages.hero.gta } : {}),
  }));

  const workflowItems = WORKFLOW_KEYS.map((key) => ({
    title: t(`workflow.steps.${key}.title`),
    description: t(`workflow.steps.${key}.stepDescription`),
  }));

  return (
    <>
      <JsonLd data={buildFAQPageSchema(faqItems)} />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref={driverPortalUrl}
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref={contactHref}
        variant="light-centered"
        illustration={<HeroPhoto image={siteImages.hero.partner} priority />}
      />

      <FeatureSection
        id="vehicles"
        label={t("vehicles.label")}
        title={t("vehicles.title")}
        subtitle={t("vehicles.subtitle")}
        items={vehicleItems}
      />
      <section className="pb-16 md:pb-20 bg-white">
        <Container size="narrow">
          <p className="text-sm text-muted leading-relaxed border-l-4 border-secondary/40 pl-4">
            {t("vehicles.licenceNote")}
          </p>
        </Container>
      </section>

      <FeatureSection
        label={t("pillars.label")}
        title={t("pillars.title")}
        subtitle={t("pillars.subtitle")}
        items={pillarItems}
        variant="pillars"
        className="bg-primary"
      />

      <FeatureSection
        label={t("workflow.label")}
        title={t("workflow.title")}
        subtitle={t("workflow.subtitle")}
        items={workflowItems}
        variant="rows"
        className="bg-gray-bg"
      />

      <FeatureSection
        label={t("ease.label")}
        title={t("ease.title")}
        subtitle={t("ease.subtitle")}
        items={easeItems}
      />

      <FaqSection
        label={t("faq.label")}
        title={t("faq.title")}
        items={faqItems}
        className="bg-gray-bg"
      />

      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref={driverPortalUrl}
        secondaryLabel={t("cta.secondary")}
        secondaryHref={contactHref}
        variant="gradient"
      />

      <section className="pb-12 bg-gray-bg">
        <Container size="narrow">
          <p className="text-xs text-muted leading-relaxed">{t("disclaimer")}</p>
        </Container>
      </section>
    </>
  );
}
