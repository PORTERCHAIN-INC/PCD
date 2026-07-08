import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { getNicheHeroImage, getPageHeroImage } from "@/data/site-images";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import { JsonLd } from "@/components/seo";
import { buildFAQPageSchema, buildServiceSchema } from "@/lib/seo/schema";
import type { Locale } from "@/i18n/routing";
import { business, contact } from "@/lib/seo/routes";

export type NicheLandingContent = {
  meta?: { title?: string; description?: string };
  hero: { title: string; subtitle: string };
  painPoints: { title: string; item1: string; item2: string; item3: string };
  solution?: {
    title: string;
    description: string;
    bullet1?: string;
    bullet2?: string;
    bullet3?: string;
  };
  workflow?: {
    title: string;
    description: string;
    step1Title: string;
    step1Description: string;
    step2Title: string;
    step2Description: string;
    step3Title: string;
    step3Description: string;
  };
  onboarding?: {
    title: string;
    description: string;
    step1Title: string;
    step1Description: string;
    step2Title: string;
    step2Description: string;
    step3Title: string;
    step3Description: string;
  };
  faq?: { title: string; q1: string; a1: string; q2: string; a2: string; q3: string; a3: string };
  cta: { title: string; description: string; primary: string; secondary: string };
};

interface IndustryLandingViewProps {
  locale: Locale;
  slug: string;
  niche: NicheLandingContent;
  cityLinks: { href: string; label: string }[];
  localCityLinks: { href: string; label: string }[];
  relatedTitle?: string;
}

export default function IndustryLandingView({
  locale,
  slug,
  niche,
  cityLinks,
  localCityLinks,
  relatedTitle = "Delivery in your city",
}: IndustryLandingViewProps) {
  const businessHref = business(locale, { from: `industry/${slug}` });
  const contactHref = contact(locale, { from: `industry/${slug}` });
  const heroImage = slug.startsWith("campaigns/")
    ? getPageHeroImage(slug)
    : getNicheHeroImage(slug);
  const faqItems = niche.faq
    ? [
        { question: niche.faq.q1, answer: niche.faq.a1 },
        { question: niche.faq.q2, answer: niche.faq.a2 },
        { question: niche.faq.q3, answer: niche.faq.a3 },
      ]
    : [];
  const solutionBullets = niche.solution
    ? [niche.solution.bullet1, niche.solution.bullet2, niche.solution.bullet3].filter(
        (b): b is string => Boolean(b)
      )
    : [];
  const workflow = niche.workflow;
  const onboarding = niche.onboarding;

  return (
    <>
      <JsonLd
        data={[
          faqItems.length ? buildFAQPageSchema(faqItems) : null,
          niche.solution
            ? buildServiceSchema({
                name: niche.solution.title,
                description: niche.meta?.description,
              })
            : null,
        ].filter(Boolean)}
      />
      <HeroSection
        badge="Industries"
        title={niche.hero.title}
        subtitle={niche.hero.subtitle}
        primaryCta={niche.cta.primary}
        primaryHref={businessHref}
        secondaryCta={niche.cta.secondary}
        secondaryHref={contactHref}
        variant="light-centered"
        illustration={<HeroPhoto image={heroImage} />}
        trackSource={`industry/${slug}`}
      />
      <FeatureSection
        label="Challenges"
        title={niche.painPoints.title}
        items={[
          { title: niche.painPoints.item1, description: "" },
          { title: niche.painPoints.item2, description: "" },
          { title: niche.painPoints.item3, description: "" },
        ]}
      />
      {niche.solution && (
        <FeatureSection
          label="Solution"
          title={niche.solution.title}
          subtitle={niche.solution.description}
          items={solutionBullets.map((b) => ({ title: b, description: "" }))}
        />
      )}
      {workflow && (
        <FeatureSection
          label="Workflow"
          title={workflow.title}
          subtitle={workflow.description}
          items={[
            { title: workflow.step1Title, description: workflow.step1Description },
            { title: workflow.step2Title, description: workflow.step2Description },
            { title: workflow.step3Title, description: workflow.step3Description },
          ]}
        />
      )}
      {onboarding && (
        <FeatureSection
          label="Onboarding"
          title={onboarding.title}
          subtitle={onboarding.description}
          items={[
            { title: onboarding.step1Title, description: onboarding.step1Description },
            { title: onboarding.step2Title, description: onboarding.step2Description },
            { title: onboarding.step3Title, description: onboarding.step3Description },
          ]}
        />
      )}
      <InternalLinksBlock title={relatedTitle} links={cityLinks} />
      <InternalLinksBlock title="Local delivery by city" links={localCityLinks} />
      {faqItems.length > 0 && niche.faq && <FaqSection title={niche.faq.title} items={faqItems} />}
      <CtaSection
        title={niche.cta.title}
        subtitle={niche.cta.description}
        primaryLabel={niche.cta.primary}
        primaryHref={businessHref}
        secondaryLabel={niche.cta.secondary}
        secondaryHref={contactHref}
        variant="gradient"
        trackSource={`industry/${slug}`}
      />
    </>
  );
}
