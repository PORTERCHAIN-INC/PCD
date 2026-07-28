import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { getNicheHeroImage, getPageHeroImage } from "@/data/site-images";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import PageBreadcrumbs, { type BreadcrumbItem } from "@/components/seo/PageBreadcrumbs";
import { JsonLd } from "@/components/seo";
import { buildFAQPageSchema, buildServiceSchema } from "@/lib/seo/schema";
import type { Locale } from "@/i18n/routing";
import { contact, localePath, quoteContact } from "@/lib/seo/routes";
import PersonaAudienceSection from "@/components/seo/PersonaAudienceSection";
import { buildPersonaItems, collectNicheFaqItems } from "@/lib/seo/niche-personas";
import { CONSTRUCTION_NICHE_SLUGS } from "@/lib/seo/niche-landing";
import { buildProductLinksForNiche } from "@/lib/seo/internal-linking";
import type { SeoSectionLabels } from "@/components/seo/seo-section-labels";
import Container from "@/components/ui/Container";
import FadeIn from "@/components/corporate/motion/FadeIn";

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
  vehicleFit?: {
    title: string;
    description: string;
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
    step2Description?: string;
    step3Title: string;
    step3Description: string;
  };
  coverage?: {
    title: string;
    description: string;
  };
  serviceAreaRelevance?: {
    title: string;
    description: string;
  };
  inquiryHeading?: string;
  inquirySubheadline?: string;
  personas?: {
    label?: string;
    title: string;
    subtitle?: string;
    trustLinkLabel?: string;
    items?: Partial<
      Record<
        | "vendor"
        | "contractor"
        | "projectManager"
        | "operations"
        | "tradePartner"
        | "architect"
        | "legalProcurement",
        { title: string; description: string }
      >
    >;
  };
  faq?: {
    title: string;
    q1: string;
    a1: string;
    q2: string;
    a2: string;
    q3: string;
    a3?: string;
    q4?: string;
    a4?: string;
    q5?: string;
    a5?: string;
    q6?: string;
    a6?: string;
    q7?: string;
    a7?: string;
  };
  cta: { title: string; description: string; primary: string; secondary: string };
};

interface IndustryLandingViewProps {
  locale: Locale;
  slug: string;
  niche: NicheLandingContent;
  cityLinks: { href: string; label: string }[];
  localCityLinks: { href: string; label: string }[];
  relatedTitle?: string;
  sectionLabels: SeoSectionLabels;
  breadcrumbs?: BreadcrumbItem[];
}

export default function IndustryLandingView({
  locale,
  slug,
  niche,
  cityLinks,
  localCityLinks,
  relatedTitle,
  sectionLabels,
  breadcrumbs,
}: IndustryLandingViewProps) {
  const source = `industry/${slug}`;
  const contactHref = contact(locale, { from: source });
  const quoteHref = quoteContact(locale, source);
  const productLinks = buildProductLinksForNiche(locale, slug, source);
  const heroImage = slug.startsWith("campaigns/")
    ? getPageHeroImage(slug)
    : getNicheHeroImage(slug);
  const faqItems = collectNicheFaqItems(niche.faq);
  const isConstructionNiche = (CONSTRUCTION_NICHE_SLUGS as readonly string[]).includes(slug);
  const personaContent = isConstructionNiche
    ? buildPersonaItems(
        niche.personas,
        localePath(locale, "trust"),
        niche.personas?.trustLinkLabel ?? "Trust & documentation"
      )
    : null;
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
      {breadcrumbs && breadcrumbs.length > 0 && <PageBreadcrumbs items={breadcrumbs} />}
      <HeroSection
        badge={sectionLabels.industries}
        title={niche.hero.title}
        subtitle={niche.hero.subtitle}
        primaryCta={niche.cta.primary}
        primaryHref={quoteHref}
        secondaryCta={niche.cta.secondary}
        secondaryHref={contactHref}
        variant="light-centered"
        illustration={<HeroPhoto image={heroImage} />}
        trackSource={source}
      />
      <FeatureSection
        label={sectionLabels.challenges}
        title={niche.painPoints.title}
        items={[
          { title: niche.painPoints.item1, description: "" },
          { title: niche.painPoints.item2, description: "" },
          { title: niche.painPoints.item3, description: "" },
        ]}
      />
      {niche.solution && (
        <FeatureSection
          label={sectionLabels.solution}
          title={niche.solution.title}
          subtitle={niche.solution.description}
          items={solutionBullets.map((b) => ({ title: b, description: "" }))}
        />
      )}
      {(niche.vehicleFit || niche.coverage || niche.serviceAreaRelevance) && (
        <section className="site-section bg-gray-bg">
          <Container>
            <div className="grid gap-5 md:grid-cols-2">
              {[niche.vehicleFit, niche.coverage, niche.serviceAreaRelevance]
                .filter((item): item is NonNullable<typeof item> => Boolean(item))
                .map((item, index) => (
                  <FadeIn key={item.title} delay={index * 0.08}>
                    <article className="card-surface h-full border-t-2 border-t-secondary p-7">
                      <h2 className="text-xl font-semibold tracking-tight text-primary">
                        {item.title}
                      </h2>
                      <p className="mt-3 leading-relaxed text-muted">{item.description}</p>
                    </article>
                  </FadeIn>
                ))}
            </div>
          </Container>
        </section>
      )}
      {personaContent && <PersonaAudienceSection content={personaContent} />}
      {workflow && (
        <FeatureSection
          label={sectionLabels.workflow}
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
          label={sectionLabels.onboarding}
          title={onboarding.title}
          subtitle={onboarding.description}
          items={[
            { title: onboarding.step1Title, description: onboarding.step1Description },
            {
              title: onboarding.step2Title,
              description: onboarding.step2Description ?? "",
            },
            { title: onboarding.step3Title, description: onboarding.step3Description },
          ]}
        />
      )}
      <InternalLinksBlock
        title={relatedTitle ?? sectionLabels.relatedPages}
        links={[...cityLinks, ...localCityLinks, ...productLinks].filter(
          (link, index, all) => all.findIndex((item) => item.href === link.href) === index
        )}
      />
      {faqItems.length > 0 && niche.faq && <FaqSection title={niche.faq.title} items={faqItems} />}
      {(niche.inquiryHeading || niche.inquirySubheadline) && (
        <section className="site-section bg-white">
          <Container size="narrow" className="text-center">
            {niche.inquiryHeading && (
              <h2 className="text-2xl font-semibold tracking-tight text-primary">
                {niche.inquiryHeading}
              </h2>
            )}
            {niche.inquirySubheadline && (
              <p className="mt-3 text-muted leading-relaxed">{niche.inquirySubheadline}</p>
            )}
          </Container>
        </section>
      )}
      <CtaSection
        title={niche.cta.title}
        subtitle={niche.cta.description}
        primaryLabel={niche.cta.primary}
        primaryHref={quoteHref}
        secondaryLabel={niche.cta.secondary}
        secondaryHref={contactHref}
        variant="gradient"
        trackSource={source}
      />
    </>
  );
}
