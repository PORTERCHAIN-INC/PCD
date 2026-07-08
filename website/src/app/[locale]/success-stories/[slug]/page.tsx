import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { getNicheHeroImage } from "@/data/site-images";
import CtaSection from "@/components/corporate/sections/CtaSection";
import { JsonLd } from "@/components/seo";
import { SUCCESS_STORIES, getSuccessStoryBySlug } from "@/lib/seo/content/success-stories";
import { buildArticleSchema, buildReviewSchema } from "@/lib/seo/schema";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { INDUSTRY_PAGE_LABELS } from "@/lib/seo/internal-linking";
import { business, contact, industrySlug } from "@/lib/seo/routes";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    for (const story of SUCCESS_STORIES) {
      params.push({ locale, slug: story.slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const story = getSuccessStoryBySlug(slug);
  if (!story) return {};
  return buildPageMetadata(locale, `success-stories/${slug}`, story.title, story.description);
}

export default async function SuccessStoryPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const story = getSuccessStoryBySlug(slug);
  if (!story) notFound();

  const loc = locale as Locale;
  const schemas = [
    buildArticleSchema({ headline: story.headline, description: story.description }),
    story.quote
      ? buildReviewSchema({ reviewBody: story.quote, authorName: story.quoteAttribution })
      : null,
  ].filter(Boolean);

  return (
    <CorporateShell>
      <JsonLd data={schemas} />
      <HeroSection
        badge="Success story"
        title={story.headline}
        subtitle={story.challenge}
        primaryCta="Talk to us"
        primaryHref={business(loc, { from: `success-stories/${slug}` })}
        secondaryCta="Contact"
        secondaryHref={contact(loc, { from: `success-stories/${slug}` })}
        variant="light-centered"
        illustration={<HeroPhoto image={getNicheHeroImage(story.industrySlug)} />}
      />
      <section className="site-section bg-white">
        <Container size="narrow" className="space-y-8 text-muted leading-relaxed">
          <div>
            <h2 className="text-xl font-semibold text-primary">Solution</h2>
            <p className="mt-3">{story.solution}</p>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-primary">Outcome</h2>
            <p className="mt-3">{story.outcome}</p>
            {story.outcomeMetric && (
              <p className="mt-2 font-medium text-primary">{story.outcomeMetric}</p>
            )}
          </div>
          {story.quote && (
            <blockquote className="border-l-4 border-secondary pl-4 italic text-primary">
              “{story.quote}”
              {story.quoteAttribution && (
                <footer className="mt-2 text-sm not-italic text-muted">
                  — {story.quoteAttribution}
                </footer>
              )}
            </blockquote>
          )}
          <p>
            <Link
              href={industrySlug(loc, story.industrySlug)}
              className="text-secondary font-medium hover:underline"
            >
              Learn more about {INDUSTRY_PAGE_LABELS[story.industrySlug] ?? story.industrySlug}{" "}
              delivery →
            </Link>
          </p>
        </Container>
      </section>
      <CtaSection
        title="Ready for similar results?"
        primaryLabel="Get started"
        primaryHref={business(loc, { from: `success-stories/${slug}` })}
        secondaryLabel="Contact us"
        secondaryHref={contact(loc)}
        variant="gradient"
      />
    </CorporateShell>
  );
}
