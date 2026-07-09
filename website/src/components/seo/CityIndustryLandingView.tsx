import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { getPageHeroImage } from "@/data/site-images";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import PlatformBridgeSection from "@/components/seo/PlatformBridgeSection";
import PageBreadcrumbs, { type BreadcrumbItem } from "@/components/seo/PageBreadcrumbs";
import { JsonLd } from "@/components/seo";
import { buildFAQPageSchema, buildServiceSchema } from "@/lib/seo/schema";
import type { Locale } from "@/i18n/routing";
import { contact, demoContact, platform } from "@/lib/seo/routes";
import { buildProductLinksForIndustrySeoSlug } from "@/lib/seo/internal-linking";
import type { CityIndustryContent } from "@/lib/seo/city-industry-delivery";

interface CityIndustryLandingViewProps {
  locale: Locale;
  city: string;
  industrySlug: string;
  content: CityIndustryContent;
  industryLinks: { href: string; label: string }[];
  relatedTitle?: string;
  trackSource?: string;
  breadcrumbs?: BreadcrumbItem[];
}

export default function CityIndustryLandingView({
  locale,
  city,
  industrySlug,
  content,
  industryLinks,
  relatedTitle = "Explore by industry",
  trackSource,
  breadcrumbs,
}: CityIndustryLandingViewProps) {
  const path = trackSource ?? `${city}/${industrySlug}`;
  const contactHref = contact(locale, { from: path });
  const demoHref = demoContact(locale, path);
  const platformHref = platform(locale, { from: path });
  const productLinks = buildProductLinksForIndustrySeoSlug(locale, industrySlug, path);

  return (
    <>
      <JsonLd
        data={[
          buildFAQPageSchema(content.faq.items),
          buildServiceSchema({ name: content.hero.title, description: content.meta.description }),
        ].filter(Boolean)}
      />
      {breadcrumbs && breadcrumbs.length > 0 && <PageBreadcrumbs items={breadcrumbs} />}
      <HeroSection
        badge="Local delivery"
        title={content.hero.title}
        subtitle={content.hero.subtitle}
        primaryCta={content.cta.primary}
        primaryHref={demoHref}
        secondaryCta={content.cta.secondary}
        secondaryHref={contactHref}
        variant="light-centered"
        illustration={<HeroPhoto image={getPageHeroImage(industrySlug)} />}
        trackSource={path}
      />
      <PlatformBridgeSection from={path} />
      <FeatureSection
        label="Local challenges"
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
      <FeatureSection
        label="Industry fit"
        title={content.industryRelevance.title}
        subtitle={content.industryRelevance.description}
        items={content.industryRelevance.bullets.map((b) => ({ title: b, description: "" }))}
      />
      <FeatureSection
        label="How it works"
        title={content.operationalFit.title}
        subtitle={content.operationalFit.description}
        items={content.operationalFit.steps.map((s) => ({
          title: s.title,
          description: s.description,
        }))}
      />
      <InternalLinksBlock title={relatedTitle} links={industryLinks} />
      <InternalLinksBlock title="Capacity & solutions" links={productLinks} />
      <FaqSection title={content.faq.title} items={content.faq.items} />
      <CtaSection
        title={content.cta.title}
        subtitle={content.cta.description}
        primaryLabel={content.cta.primary}
        primaryHref={demoHref}
        secondaryLabel={content.cta.secondary}
        secondaryHref={platformHref}
        variant="gradient"
        trackSource={path}
      />
    </>
  );
}
