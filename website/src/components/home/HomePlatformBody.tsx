import { getTranslations } from "next-intl/server";
import BentoSection from "@/components/corporate/sections/BentoSection";
import TimelineSection from "@/components/corporate/sections/TimelineSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CardGridSection from "@/components/corporate/sections/CardGridSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import { RelatedResourcesSection } from "@/components/corporate/sections/CardGridSection";
import Industries from "@/components/sections/Industries";
import {
  collectCardItems,
  collectFaqItems,
  collectResourceItems,
  collectTimelineSteps,
} from "@/lib/corporate-content";
import { AlertTriangle, Leaf, Map, Route, Shield, Users } from "lucide-react";

export default async function HomePlatformBody() {
  const t = await getTranslations("corporate.home");

  const bentoItems = [
    { title: t("bento.dispatch.title"), description: t("bento.dispatch.description") },
    { title: t("bento.routing.title"), description: t("bento.routing.description") },
    { title: t("bento.visibility.title"), description: t("bento.visibility.description") },
    { title: t("bento.compliance.title"), description: t("bento.compliance.description") },
    { title: t("bento.integrations.title"), description: t("bento.integrations.description") },
    { title: t("bento.analytics.title"), description: t("bento.analytics.description") },
  ];

  const featureItems = [
    {
      title: t("features.items.0.title"),
      description: t("features.items.0.description"),
      icon: Shield,
    },
    {
      title: t("features.items.1.title"),
      description: t("features.items.1.description"),
      icon: Route,
    },
    {
      title: t("features.items.2.title"),
      description: t("features.items.2.description"),
      icon: AlertTriangle,
    },
    {
      title: t("features.items.3.title"),
      description: t("features.items.3.description"),
      icon: Users,
    },
    {
      title: t("features.items.4.title"),
      description: t("features.items.4.description"),
      icon: Leaf,
    },
    {
      title: t("features.items.5.title"),
      description: t("features.items.5.description"),
      icon: Map,
    },
  ];

  return (
    <>
      <CardGridSection
        label={t("pillars.label")}
        title={t("pillars.title")}
        subtitle={t("pillars.subtitle")}
        items={collectCardItems(t, "pillars.items", 3)}
        className="bg-gray-bg"
      />
      <BentoSection
        label={t("bento.label")}
        title={t("bento.title")}
        subtitle={t("bento.subtitle")}
        items={bentoItems}
      />
      <CtaSection
        title={t("wedge.title")}
        subtitle={t("wedge.subtitle")}
        primaryLabel={t("wedge.cta")}
        primaryHref={t("wedge.href")}
        secondaryLabel={t("pillars.cta")}
        secondaryHref="/business#fleet"
        variant="light"
        trackSource="home-wedge"
      />
      <TimelineSection
        label={t("timeline.label")}
        title={t("timeline.title")}
        subtitle={t("timeline.subtitle")}
        steps={collectTimelineSteps(t, "timeline.steps", 4)}
        variant="horizontal"
        className="bg-white"
      />
      <FeatureSection
        label={t("features.label")}
        title={t("features.title")}
        subtitle={t("features.subtitle")}
        items={featureItems}
        variant="grid"
        className="bg-gray-bg"
      />
      <Industries />
      <CtaSection
        title={t("caseStudy.title")}
        subtitle={t("caseStudy.subtitle")}
        primaryLabel={t("caseStudy.cta")}
        primaryHref={t("caseStudy.href")}
        secondaryLabel={t("hero.secondaryCta")}
        secondaryHref="/business#fleet"
        variant="dark"
        trackSource="home-case-study"
      />
      <CtaSection
        title={t("developerStrip.title")}
        subtitle={t("developerStrip.subtitle")}
        primaryLabel={t("developerStrip.primary")}
        primaryHref={t("developerStrip.href")}
        secondaryLabel={t("cta.primary")}
        secondaryHref="/contact?intent=quote&from=home-operations"
        variant="gradient"
        trackSource="home-developers"
      />
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="/contact?intent=quote&from=home-cta"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/business"
        variant="dark"
        trackSource="home-cta"
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
    </>
  );
}
