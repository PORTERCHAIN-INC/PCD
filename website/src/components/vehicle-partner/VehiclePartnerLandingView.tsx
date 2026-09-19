import { getTranslations } from "next-intl/server";
import type { FeatureIconName } from "@/components/corporate/icons/feature-icons";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import Container from "@/components/ui/Container";
import { JsonLd } from "@/components/seo";
import { buildFAQPageSchema } from "@/lib/seo/schema";
import { siteImages, getVehiclePartnerImage } from "@/data/site-images";
import VehiclePartnerHero from "@/components/vehicle-partner/VehiclePartnerHero";
import HubShell from "@/components/hub/HubShell";
import HubMapStage from "@/components/hub/HubMapStage";
import HubOfferCards from "@/components/hub/HubOfferCards";
import HubStatusChip from "@/components/hub/HubStatusChip";
import HubTrustStrip from "@/components/hub/HubTrustStrip";
import { driverSignInUrl } from "@/data/portal-links";
import { HUB_FROM } from "@/lib/marketing/config";
import type { Locale } from "@/i18n/routing";

const VEHICLE_KEYS = ["sedan", "suv", "pickup", "van", "boxTruck"] as const;
const VEHICLE_ICONS: Record<(typeof VEHICLE_KEYS)[number], FeatureIconName> = {
  sedan: "car",
  suv: "carFront",
  pickup: "truck",
  van: "package",
  boxTruck: "box",
};

const PILLAR_KEYS = ["routes", "earnings", "support", "multiple"] as const;
const EASE_KEYS = ["clarity", "tools", "fleet", "local"] as const;
const WORKFLOW_KEYS = ["step1", "step2", "step3"] as const;

type Props = { locale: Locale };

export default async function VehiclePartnerLandingView({ locale }: Props) {
  const t = await getTranslations("vehiclePartner");
  const tFacade = await getTranslations("vehiclePartner.hubFacade");
  const tTrust = await getTranslations("vehiclePartner.trustStrip");

  const faqItems = t.raw("faq.items") as { question: string; answer: string }[];
  const contactHref = `/${locale}/contact?from=${HUB_FROM.drivers}`;

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

  const offers = [
    {
      id: "a1",
      title: tFacade("offers.a.title"),
      badge: tFacade("offers.a.badge"),
      meta: tFacade("offers.a.meta"),
    },
    {
      id: "a2",
      title: tFacade("offers.b.title"),
      badge: tFacade("offers.b.badge"),
      meta: tFacade("offers.b.meta"),
    },
    {
      id: "a3",
      title: tFacade("offers.c.title"),
      badge: tFacade("offers.c.badge"),
      meta: tFacade("offers.c.meta"),
    },
  ];

  return (
    <HubShell>
      <JsonLd data={buildFAQPageSchema(faqItems)} />
      <VehiclePartnerHero locale={locale} />

      <section
        className="border-b border-primary/6 bg-[#F4F6FA]"
        aria-labelledby="drivers-hub-facade"
      >
        <Container className="py-10 sm:py-12">
          <div className="mb-6 flex flex-wrap items-center gap-2">
            <h2 id="drivers-hub-facade" className="text-lg font-semibold text-primary sm:text-xl">
              {tFacade("title")}
            </h2>
            <HubStatusChip label={tFacade("chip")} tone="info" />
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <HubOfferCards items={offers} illustrativeNote={tFacade("illustrativeNote")} />
            <div className="space-y-4">
              <HubMapStage title={tFacade("mapTitle")} subtitle={tFacade("mapSubtitle")} />
              <a
                href={driverSignInUrl}
                className="inline-flex w-full items-center justify-center rounded-xl bg-secondary px-5 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8] sm:w-auto"
              >
                {tFacade("portalCta")}
              </a>
            </div>
          </div>
        </Container>
      </section>

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

      <HubTrustStrip
        eyebrow={tTrust("eyebrow")}
        title={tTrust("title")}
        body={tTrust("body")}
        companyLabel={tTrust("company")}
        trustLabel={tTrust("trust")}
        contactLabel={tTrust("contact")}
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
        primaryHref="#apply"
        secondaryLabel={t("cta.secondary")}
        secondaryHref={contactHref}
        variant="gradient"
      />

      <section className="pb-12 bg-gray-bg">
        <Container size="narrow">
          <p className="text-xs text-muted leading-relaxed">{t("disclaimer")}</p>
        </Container>
      </section>
    </HubShell>
  );
}
