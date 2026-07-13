import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { MapPin } from "lucide-react";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import { siteImages } from "@/data/site-images";
import { SERVICE_AREA_REGIONS } from "@/lib/solutions-hub-config";
import { SERVICE_AREA_SLUGS } from "@/lib/seo/service-areas";
import type { Locale } from "@/i18n/routing";

interface ServiceAreasHubViewProps {
  locale: Locale;
}

export default async function ServiceAreasHubView({ locale: _locale }: ServiceAreasHubViewProps) {
  const t = await getTranslations("serviceAreasIndex");
  const tBc = await getTranslations("corporate.breadcrumbs");
  const source = "service-areas";

  const outcomeItems = [0, 1, 2, 3].map((i) => ({
    title: t(`outcomes.items.${i}.title`),
    description: t(`outcomes.items.${i}.description`),
  }));

  const faqItems = [0, 1, 2, 3].map((i) => ({
    question: t(`faq.items.${i}.q`),
    answer: t(`faq.items.${i}.a`),
  }));

  const knownSlugs = new Set<string>(SERVICE_AREA_SLUGS);

  return (
    <>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: t("breadcrumb") }]} />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("cta.primary")}
        primaryHref={`/contact?intent=quote&from=${source}`}
        secondaryCta={t("cta.secondary")}
        secondaryHref="/solutions"
        variant="light-centered"
        illustration={<HeroPhoto image={siteImages.hero.gta} />}
        trackSource={source}
      />

      <section className="site-section bg-white">
        <Container>
          <SectionHeader title={t("coverage.title")} subtitle={t("coverage.description")} />
          <p className="mt-6 max-w-3xl text-muted leading-relaxed">{t("hubIntro")}</p>
        </Container>
      </section>

      {SERVICE_AREA_REGIONS.map((region) => {
        const slugs = region.slugs.filter((slug) => knownSlugs.has(slug));
        if (slugs.length === 0) return null;
        return (
          <section key={region.key} className="site-section bg-gray-bg border-t border-primary/6">
            <Container>
              <h2 className="text-lg font-semibold text-primary tracking-tight">
                {t(`regions.${region.key}.label`)}
              </h2>
              <p className="mt-2 text-sm text-muted max-w-2xl">
                {t(`regions.${region.key}.description`)}
              </p>
              <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
                {slugs.map((slug) => (
                  <Link
                    key={slug}
                    href={`/service-areas/${slug}`}
                    className="group flex flex-col rounded-2xl border border-primary/8 bg-white p-4 sm:p-5 shadow-premium transition-all hover:border-secondary/30 hover:shadow-[0_12px_40px_-12px_rgba(10,22,40,0.12)] hover:-translate-y-0.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <MapPin className="h-4 w-4 shrink-0 text-secondary mt-0.5" aria-hidden />
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                        {t(`cities.${slug}.region`)}
                      </span>
                    </div>
                    <h3 className="mt-3 text-base font-semibold text-primary group-hover:text-secondary transition-colors">
                      {t(`cities.${slug}.title`)}
                    </h3>
                    <p className="mt-2 flex-1 text-xs sm:text-sm text-muted leading-relaxed line-clamp-3">
                      {t(`cities.${slug}.tagline`)}
                    </p>
                    <span className="mt-4 text-xs font-semibold text-secondary group-hover:underline">
                      {t("cities.viewCity")} →
                    </span>
                  </Link>
                ))}
              </div>
            </Container>
          </section>
        );
      })}

      <FeatureSection
        label={t("vehicles.label")}
        title={t("vehicles.title")}
        subtitle={t("vehicles.description")}
        items={outcomeItems}
        variant="grid"
        className="bg-white"
      />

      <FaqSection label={t("faq.label")} title={t("faq.title")} items={faqItems} />

      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.description")}
        primaryLabel={t("cta.primary")}
        primaryHref={`/contact?intent=quote&from=${source}`}
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/business#fleet"
        variant="gradient"
        trackSource={source}
      />
    </>
  );
}
