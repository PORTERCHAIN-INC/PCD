import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HeroSection from "@/components/corporate/sections/HeroSection";
import TimelineSection from "@/components/corporate/sections/TimelineSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import LinkButton from "@/components/corporate/ui/LinkButton";
import HowItWorksFleet from "@/components/how-it-works/HowItWorksFleet";
import HowItWorksSolutionCards from "@/components/how-it-works/HowItWorksSolutionCards";
import { collectTimelineSteps } from "@/lib/corporate-content";
import { solutionVerticalPath, type SolutionVerticalSlug } from "@/lib/solutions-verticals";
import { CORE_SERVICE_AREA_SLUGS } from "@/lib/seo/service-areas";
import type { FeatureIconName } from "@/components/corporate/icons/feature-icons";
import type { Locale } from "@/i18n/routing";

const SOLUTION_KEYS = [
  {
    key: "wholesale",
    vertical: "wholesale" as SolutionVerticalSlug,
    icon: "layers" as FeatureIconName,
  },
  {
    key: "medical",
    vertical: "medical" as SolutionVerticalSlug,
    icon: "shieldCheck" as FeatureIconName,
  },
  {
    key: "foodBeverage",
    vertical: "food-beverage" as SolutionVerticalSlug,
    icon: "package" as FeatureIconName,
  },
  {
    key: "construction",
    vertical: "construction" as SolutionVerticalSlug,
    icon: "truck" as FeatureIconName,
  },
] as const;

const OPERATE_ICONS = ["layers", "map", "radio", "truck"] as const satisfies FeatureIconName[];

const AREA_LABELS: Record<(typeof CORE_SERVICE_AREA_SLUGS)[number], string> = {
  toronto: "Toronto",
  mississauga: "Mississauga",
  brampton: "Brampton",
  vaughan: "Vaughan",
  markham: "Markham",
  oakville: "Oakville",
  hamilton: "Hamilton",
  "kitchener-waterloo": "Kitchener–Waterloo",
};

type Props = { locale: Locale };

export default async function HowPorterchainWorksView({ locale }: Props) {
  void locale;
  const t = await getTranslations("corporate.howPorterchainWorks");
  const tBc = await getTranslations("corporate.breadcrumbs");
  const source = "how-porterchain-works";

  const solutionItems = SOLUTION_KEYS.map(({ key, vertical, icon }) => ({
    key,
    href: solutionVerticalPath(vertical),
    title: t(`solutions.items.${key}.title`),
    description: t(`solutions.items.${key}.description`),
    icon,
    viewLabel: t("solutions.view"),
  }));

  const operateItems = OPERATE_ICONS.map((icon, i) => ({
    title: t(`operate.items.${i}.title`),
    description: t(`operate.items.${i}.description`),
    icon,
  }));

  return (
    <>
      <PageBreadcrumbs
        items={[{ label: tBc("home"), href: "/" }, { label: tBc("howPorterchainWorks") }]}
      />

      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref={`/business?from=${source}#inquiry`}
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/business"
        variant="light-centered"
      />

      <div id="how-it-works" className="scroll-mt-24">
        <TimelineSection
          label={t("steps.label")}
          title={t("steps.title")}
          subtitle={t("steps.subtitle")}
          steps={collectTimelineSteps(t, "steps.items", 4)}
          variant="horizontal"
          className="bg-white"
        />
      </div>

      <section id="solutions" className="site-section bg-gray-bg scroll-mt-24">
        <Container>
          <SectionHeader
            label={t("solutions.label")}
            title={t("solutions.title")}
            subtitle={t("solutions.subtitle")}
          />
          <HowItWorksSolutionCards items={solutionItems} />
          <div className="mt-8 flex justify-center">
            <LinkButton href="/solutions" variant="outline" showArrow trackSource={source}>
              {t("solutions.all")}
            </LinkButton>
          </div>
        </Container>
      </section>

      <section id="vehicles" className="site-section bg-white scroll-mt-24">
        <Container>
          <SectionHeader
            label={t("vehicles.label")}
            title={t("vehicles.title")}
            subtitle={t("vehicles.subtitle")}
          />
          <HowItWorksFleet />
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <LinkButton href="/vehicles" variant="outline" showArrow trackSource={source}>
              {t("vehicles.all")}
            </LinkButton>
            <LinkButton href="/business#fleet" variant="ghost" trackSource={source}>
              {t("vehicles.business")}
            </LinkButton>
          </div>
        </Container>
      </section>

      <div id="operate" className="scroll-mt-24">
        <FeatureSection
          label={t("operate.label")}
          title={t("operate.title")}
          subtitle={t("operate.subtitle")}
          items={operateItems}
          variant="grid"
          className="bg-gray-bg"
        />
        <Container className="-mt-4 pb-12 sm:pb-14 flex justify-center">
          <LinkButton href="/platform" variant="outline" showArrow trackSource={source}>
            {t("operate.more")}
          </LinkButton>
        </Container>
      </div>

      <section id="service-areas" className="site-section bg-white scroll-mt-24">
        <Container>
          <SectionHeader
            label={t("areas.label")}
            title={t("areas.title")}
            subtitle={t("areas.subtitle")}
          />
          <div className="flex flex-wrap justify-center gap-2.5 sm:gap-3">
            {CORE_SERVICE_AREA_SLUGS.map((slug, i) => (
              <FadeIn key={slug} delay={i * 0.04}>
                <Link
                  href={`/service-areas/${slug}`}
                  className="inline-flex items-center rounded-full border border-secondary/20 bg-secondary/[0.06] px-4 py-2 text-sm font-semibold text-primary transition-colors hover:border-secondary/40 hover:bg-secondary hover:text-white"
                >
                  {AREA_LABELS[slug]}
                </Link>
              </FadeIn>
            ))}
          </div>
          <p className="mt-6 text-center text-sm text-muted max-w-2xl mx-auto leading-relaxed">
            {t("areas.note")}
          </p>
          <div className="mt-8 flex justify-center">
            <LinkButton href="/service-areas" variant="outline" showArrow trackSource={source}>
              {t("areas.all")}
            </LinkButton>
          </div>
        </Container>
      </section>

      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref={`/business?from=${source}#inquiry`}
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/business"
        variant="gradient"
        trackSource={source}
      />
    </>
  );
}
