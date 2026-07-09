import { getTranslations } from "next-intl/server";
import HeroSection from "@/components/corporate/sections/HeroSection";
import CardGridSection from "@/components/corporate/sections/CardGridSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import LinkButton from "@/components/corporate/ui/LinkButton";
import FadeIn from "@/components/corporate/motion/FadeIn";
import { collectCardItems, collectFaqItems } from "@/lib/corporate-content";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export default async function PricingPageView() {
  const t = await getTranslations("corporate.pricing");
  const tBc = await getTranslations("corporate.breadcrumbs");

  const tiers = [0, 1, 2].map((i) => ({
    name: t(`tiers.items.${i}.name`),
    price: t(`tiers.items.${i}.price`),
    description: t(`tiers.items.${i}.description`),
    features: [
      t(`tiers.items.${i}.feature0`),
      t(`tiers.items.${i}.feature1`),
      t(`tiers.items.${i}.feature2`),
    ],
    cta: t(`tiers.items.${i}.cta`),
    href:
      i === 2
        ? "/contact?intent=quote&from=pricing-dedicated"
        : i === 1
          ? "/contact?intent=quote&from=pricing-recurring"
          : "/contact?intent=quote&from=pricing-occasional",
    featured: i === 1,
  }));

  return (
    <>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: t("hero.badge") }]} />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="/contact?intent=quote&from=pricing"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/business#fleet"
        variant="light-centered"
      />
      <CardGridSection
        label={t("model.label")}
        title={t("model.title")}
        subtitle={t("model.subtitle")}
        items={collectCardItems(t, "model.items", 3)}
        variant="mosaic"
        className="bg-gray-bg"
      />
      <section className="site-section bg-white">
        <Container>
          <SectionHeader
            label={t("tiers.label")}
            title={t("tiers.title")}
            subtitle={t("tiers.subtitle")}
          />
          <div className="grid md:grid-cols-3 gap-5">
            {tiers.map((tier, i) => (
              <FadeIn key={tier.name} delay={i * 0.06}>
                <article
                  className={cn(
                    "card-surface h-full flex flex-col p-7",
                    tier.featured && "ring-2 ring-secondary/30 border-secondary/20"
                  )}
                >
                  {tier.featured && (
                    <span className="text-xs font-semibold uppercase tracking-wider text-secondary mb-3">
                      {t("tiers.popular")}
                    </span>
                  )}
                  <h3 className="text-xl font-semibold text-primary">{tier.name}</h3>
                  <p className="mt-2 text-sm font-medium text-secondary">{tier.price}</p>
                  <p className="mt-3 text-sm text-muted leading-relaxed">{tier.description}</p>
                  <ul className="mt-5 space-y-2.5 flex-1">
                    {tier.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2 text-sm text-muted">
                        <Check className="w-4 h-4 text-secondary shrink-0 mt-0.5" aria-hidden />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-6">
                    <LinkButton href={tier.href} className="w-full justify-center" size="md">
                      {tier.cta}
                    </LinkButton>
                  </div>
                </article>
              </FadeIn>
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-muted">{t("tiers.custom")}</p>
        </Container>
      </section>
      <FaqSection
        label={t("faq.label")}
        title={t("faq.title")}
        items={collectFaqItems(t, "faq.items", 3)}
        className="bg-gray-bg"
      />
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="/contact?intent=quote&from=pricing"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/business"
        variant="gradient"
        trackSource="pricing"
      />
    </>
  );
}
