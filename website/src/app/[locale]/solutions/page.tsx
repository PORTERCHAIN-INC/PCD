import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import SolutionsTabNav from "@/components/solutions/SolutionsTabNav";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import TimelineSection from "@/components/corporate/sections/TimelineSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import LinkButton from "@/components/corporate/ui/LinkButton";
import { siteImages } from "@/data/site-images";
import { collectCardItems, collectFaqItems, collectTimelineSteps } from "@/lib/corporate-content";
import { SOLUTION_VERTICAL_SLUGS, solutionVerticalPath } from "@/lib/solutions-verticals";
import { Link } from "@/i18n/navigation";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.solutions" });
  return buildPageMetadata(locale, "solutions", t("title"), t("description"));
}

export default async function SolutionsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.solutions");
  const tBc = await getTranslations("corporate.breadcrumbs");

  const verticalCards = collectCardItems(
    t,
    "cards.items",
    SOLUTION_VERTICAL_SLUGS.length,
    SOLUTION_VERTICAL_SLUGS as unknown as string[]
  );

  const outcomeItems = [
    {
      title: t("features.items.0.title"),
      description: t("features.items.0.description"),
      icon: "timer" as const,
    },
    {
      title: t("features.items.1.title"),
      description: t("features.items.1.description"),
      icon: "shieldCheck" as const,
    },
    {
      title: t("features.items.2.title"),
      description: t("features.items.2.description"),
      icon: "eye" as const,
    },
    {
      title: t("features.items.3.title"),
      description: t("features.items.3.description"),
      icon: "barChart3" as const,
    },
  ];

  return (
    <CorporateShell>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: tBc("solutions") }]} />
      <SolutionsTabNav />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="/sign-up?intent=quote&from=solutions"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/vehicles"
        variant="light-centered"
        illustration={<HeroPhoto image={siteImages.hero.gta} />}
      />
      <section className="site-section bg-white">
        <Container>
          <SectionHeader label={t("cards.label")} title={t("cards.title")} />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {verticalCards.map((item, i) => (
              <FadeIn key={item.id ?? i} delay={i * 0.06}>
                <article className="card-surface card-surface-hover p-5 h-full flex flex-col">
                  <h3 className="text-lg font-semibold text-primary">{item.title}</h3>
                  <p className="mt-2 text-sm text-muted leading-relaxed flex-1">
                    {item.description}
                  </p>
                  {item.id && (
                    <div className="mt-4">
                      <LinkButton
                        href={solutionVerticalPath(
                          item.id as (typeof SOLUTION_VERTICAL_SLUGS)[number]
                        )}
                        size="sm"
                        showArrow
                      >
                        {t("cards.viewSolution")}
                      </LinkButton>
                    </div>
                  )}
                </article>
              </FadeIn>
            ))}
          </div>
          <p className="mt-6 text-sm text-muted">
            {t("cards.alsoBrowse")}
            <Link
              href="/business#industries"
              className="font-medium text-secondary hover:underline"
            >
              {t("cards.allIndustries")}
            </Link>
            .
          </p>
        </Container>
      </section>
      <FeatureSection
        label={t("features.label")}
        title={t("features.title")}
        items={outcomeItems}
        variant="grid"
      />
      <TimelineSection
        label={t("timeline.label")}
        title={t("timeline.title")}
        subtitle={t("timeline.subtitle")}
        steps={collectTimelineSteps(t, "timeline.steps", 4)}
        variant="horizontal"
        className="bg-gray-bg"
      />
      <FaqSection
        label={t("faq.label")}
        title={t("faq.title")}
        items={collectFaqItems(t, "faq.items", 4)}
      />
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="/sign-up?intent=quote&from=solutions"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/vehicles"
        variant="gradient"
      />
    </CorporateShell>
  );
}
