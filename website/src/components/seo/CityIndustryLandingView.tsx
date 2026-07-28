import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { getPageHeroImage } from "@/data/site-images";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import PageBreadcrumbs, { type BreadcrumbItem } from "@/components/seo/PageBreadcrumbs";
import { JsonLd } from "@/components/seo";
import { buildFAQPageSchema, buildServiceSchema } from "@/lib/seo/schema";
import dynamic from "next/dynamic";
import type { Locale } from "@/i18n/routing";
import { contact, quoteContact, platform } from "@/lib/seo/routes";
import {
  buildProductLinksForIndustrySeoSlug,
  buildIntentHubLinks,
  INTENT_HUB_FAQ_SLUGS,
} from "@/lib/seo/internal-linking";
import { getLocalizedFaqCluster } from "@/lib/seo/programmatic-content";

type CitySectionLabels = {
  localDelivery: string;
  localChallenges: string;
  industryFit: string;
  howItWorks: string;
  onboarding: string;
  capacitySolutions: string;
  intentGuides: string;
  relatedPages: string;
};
import type { CityIndustryContent } from "@/lib/seo/city-industry-delivery";
import Container from "@/components/ui/Container";
import FadeIn from "@/components/corporate/motion/FadeIn";

const PostalCoverageChecker = dynamic(() => import("@/components/seo/PostalCoverageChecker"), {
  loading: () => <div className="site-section min-h-[8rem] bg-gray-bg" aria-hidden />,
});

interface CityIndustryLandingViewProps {
  locale: Locale;
  city: string;
  industrySlug: string;
  serviceAreaSlug: string;
  content: CityIndustryContent;
  industryLinks: { href: string; label: string }[];
  relatedTitle?: string;
  sectionLabels: CitySectionLabels;
  trackSource?: string;
  breadcrumbs?: BreadcrumbItem[];
}

export default async function CityIndustryLandingView({
  locale,
  city,
  industrySlug,
  serviceAreaSlug,
  content,
  industryLinks,
  relatedTitle,
  sectionLabels,
  trackSource,
  breadcrumbs,
}: CityIndustryLandingViewProps) {
  const path = trackSource ?? `${city}/${industrySlug}`;
  const contactHref = contact(locale, { from: path });
  const quoteHref = quoteContact(locale, path);
  const platformHref = platform(locale, { from: path });
  const productLinks = buildProductLinksForIndustrySeoSlug(locale, industrySlug, path);

  const titleBySlug: Partial<Record<(typeof INTENT_HUB_FAQ_SLUGS)[number], string>> = {};
  for (const slug of INTENT_HUB_FAQ_SLUGS) {
    const cluster = await getLocalizedFaqCluster(locale, slug);
    if (cluster) titleBySlug[slug] = cluster.title;
  }
  const intentLinks = buildIntentHubLinks(locale, path, titleBySlug);

  return (
    <>
      <JsonLd
        data={[
          buildFAQPageSchema(content.faq.items),
          buildServiceSchema({
            name: content.hero.title,
            description: content.meta.description,
            geoSlug: serviceAreaSlug,
          }),
        ].filter(Boolean)}
      />
      {breadcrumbs && breadcrumbs.length > 0 && <PageBreadcrumbs items={breadcrumbs} />}
      <HeroSection
        badge={sectionLabels.localDelivery}
        title={content.hero.title}
        subtitle={content.hero.subtitle}
        primaryCta={content.cta.primary}
        primaryHref={quoteHref}
        secondaryCta={content.cta.secondary}
        secondaryHref={contactHref}
        variant="light-centered"
        illustration={<HeroPhoto image={getPageHeroImage(industrySlug)} />}
        trackSource={path}
      />
      <FeatureSection
        label={sectionLabels.localChallenges}
        title={content.localChallenges.title}
        items={content.localChallenges.items.map((item) => ({ title: item, description: "" }))}
      />
      <section className="site-section bg-white">
        <div className="site-container max-w-3xl mx-auto px-4">
          <p className="text-muted leading-relaxed">{content.localIntro.paragraph1}</p>
          {content.localIntro.paragraph2 && (
            <p className="mt-4 text-muted leading-relaxed">{content.localIntro.paragraph2}</p>
          )}
        </div>
      </section>
      {content.faq.items.length > 0 && (
        <FaqSection title={content.faq.title} items={content.faq.items} />
      )}
      <div className="perf-defer-section">
        <PostalCoverageChecker
          locale={locale}
          cityLabel={city
            .split("-")
            .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
            .join(" ")}
          trackSource={path}
        />
      </div>
      <FeatureSection
        label={sectionLabels.industryFit}
        title={content.industryRelevance.title}
        subtitle={content.industryRelevance.description}
        items={content.industryRelevance.bullets.map((b) => ({ title: b, description: "" }))}
      />
      <FeatureSection
        label={sectionLabels.howItWorks}
        title={content.operationalFit.title}
        subtitle={content.operationalFit.description}
        items={content.operationalFit.steps.map((s) => ({
          title: s.title,
          description: s.description,
        }))}
      />
      {content.coverage?.title && (
        <section className="site-section bg-gray-bg">
          <Container size="narrow">
            <FadeIn>
              <h2 className="text-2xl font-semibold text-primary tracking-tight">
                {content.coverage.title}
              </h2>
              {content.coverage.description && (
                <p className="mt-4 text-muted leading-relaxed">{content.coverage.description}</p>
              )}
            </FadeIn>
          </Container>
        </section>
      )}
      {content.onboarding?.title && content.onboarding.steps.length > 0 && (
        <FeatureSection
          label={sectionLabels.onboarding}
          title={content.onboarding.title}
          subtitle={content.onboarding.description}
          items={content.onboarding.steps.map((step) => ({
            title: step.title,
            description: step.description,
          }))}
        />
      )}
      <InternalLinksBlock
        title={relatedTitle ?? sectionLabels.relatedPages}
        links={[...industryLinks, ...intentLinks, ...productLinks].filter(
          (link, index, all) => all.findIndex((item) => item.href === link.href) === index
        )}
      />
      <CtaSection
        title={content.cta.title}
        subtitle={content.cta.description}
        primaryLabel={content.cta.primary}
        primaryHref={quoteHref}
        secondaryLabel={content.cta.secondary}
        secondaryHref={platformHref}
        variant="gradient"
        trackSource={path}
      />
    </>
  );
}
