import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import LinkButton from "@/components/corporate/ui/LinkButton";
import { NICHE_SLUGS, CONSTRUCTION_NICHE_SLUGS } from "@/lib/seo/niche-landing";
import { getPageHeroImage } from "@/data/site-images";
import type { Locale } from "@/i18n/routing";

const CONSTRUCTION_SET = new Set<string>(CONSTRUCTION_NICHE_SLUGS);
const OTHER_NICHES = NICHE_SLUGS.filter((slug) => !CONSTRUCTION_SET.has(slug));

interface IndustryHubViewProps {
  locale: Locale;
}

export default async function IndustryHubView({ locale: _locale }: IndustryHubViewProps) {
  const t = await getTranslations("corporate.industriesIndex");
  const tBc = await getTranslations("corporate.breadcrumbs");
  const source = "industry";

  const personaItems = [0, 1, 2, 3].map((i) => ({
    title: t(`personas.items.${i}.title`),
    description: t(`personas.items.${i}.description`),
  }));

  const faqItems = [0, 1, 2, 3].map((i) => ({
    question: t(`faq.items.${i}.q`),
    answer: t(`faq.items.${i}.a`),
  }));

  const renderCard = (slug: string, featured = false) => (
    <Link
      key={slug}
      href={`/industry/${slug}`}
      className={`group flex flex-col rounded-2xl border bg-white p-6 shadow-premium transition-all hover:border-secondary/30 hover:-translate-y-0.5 ${
        featured ? "border-secondary/20" : "border-primary/8"
      }`}
    >
      {featured && (
        <span className="mb-3 w-fit rounded-full bg-secondary/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-secondary">
          {t("featured.badge")}
        </span>
      )}
      <h3 className="text-lg font-semibold text-primary group-hover:text-secondary transition-colors">
        {t(`items.${slug}.title`)}
      </h3>
      <p className="mt-2 flex-1 text-sm text-muted leading-relaxed">
        {t(`items.${slug}.description`)}
      </p>
      <span className="mt-4 text-sm font-semibold text-secondary">{t("items.viewPlaybook")} →</span>
    </Link>
  );

  return (
    <>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: t("breadcrumb") }]} />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref={`/contact?intent=quote&from=${source}`}
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/solutions/construction"
        variant="light-centered"
        illustration={<HeroPhoto image={getPageHeroImage("industry")} />}
        trackSource={source}
      />

      <section className="site-section bg-white">
        <Container>
          <SectionHeader
            label={t("featured.label")}
            title={t("featured.title")}
            subtitle={t("featured.subtitle")}
          />
          <div className="grid gap-4 md:grid-cols-3">
            {CONSTRUCTION_NICHE_SLUGS.map((slug) => renderCard(slug, true))}
          </div>
          <div className="mt-6 text-center">
            <LinkButton href="/solutions/construction" showArrow trackSource={source}>
              {t("featured.solutionsCta")}
            </LinkButton>
          </div>
        </Container>
      </section>

      <section className="site-section bg-gray-bg border-t border-primary/6">
        <Container>
          <SectionHeader
            label={t("all.label")}
            title={t("all.title")}
            subtitle={t("all.subtitle")}
          />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {OTHER_NICHES.map((slug) => renderCard(slug))}
          </div>
          <p className="mt-8 text-center text-sm text-muted">
            {t("all.alsoBrowse")}{" "}
            <Link href="/solutions" className="font-semibold text-secondary hover:underline">
              {t("all.solutions")}
            </Link>
            {" · "}
            <Link href="/service-areas" className="font-semibold text-secondary hover:underline">
              {t("all.serviceAreas")}
            </Link>
          </p>
        </Container>
      </section>

      <FeatureSection
        label={t("personas.label")}
        title={t("personas.title")}
        subtitle={t("personas.subtitle")}
        items={personaItems}
        variant="grid"
      />

      <FaqSection label={t("faq.label")} title={t("faq.title")} items={faqItems} />

      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
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
