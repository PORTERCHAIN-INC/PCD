import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { getNicheHeroImage } from "@/data/site-images";
import CtaSection from "@/components/corporate/sections/CtaSection";
import AuthorCard from "@/components/blog/AuthorCard";
import { JsonLd } from "@/components/seo";
import { buildArticleSchema, buildReviewSchema } from "@/lib/seo/schema";
import { buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import {
  getLocalizedSuccessStory,
  hasProgrammaticLocale,
  listLocalizedSuccessStorySlugs,
} from "@/lib/seo/programmatic-content";
import { getAuthor } from "@/data/blog-authors";
import { INDUSTRY_PAGE_LABELS } from "@/lib/seo/internal-linking";
import { business, contact, industrySlug } from "@/lib/seo/routes";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export async function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    const slugs = await listLocalizedSuccessStorySlugs(locale as Locale);
    for (const slug of slugs) {
      params.push({ locale, slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const story = await getLocalizedSuccessStory(locale as Locale, slug);
  if (!story) return {};
  const localized = await hasProgrammaticLocale(locale, "successStories", slug);
  return buildProgrammaticPageMetadata(
    locale,
    `success-stories/${slug}`,
    story.title,
    story.description,
    localized
  );
}

export default async function SuccessStoryPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const story = await getLocalizedSuccessStory(locale as Locale, slug);
  if (!story) notFound();

  const loc = locale as Locale;
  const t = await getTranslations("corporate.seo.sectionLabels");
  const author = story.authorId ? getAuthor(story.authorId) : null;
  const showMetric = Boolean(story.permissioned && story.outcomeMetric);
  const schemas = [
    buildArticleSchema({
      headline: story.headline,
      description: story.description,
      authorPerson: author ? { name: author.name, jobTitle: author.role } : undefined,
    }),
    story.permissioned && story.quote
      ? buildReviewSchema({ reviewBody: story.quote, authorName: story.quoteAttribution })
      : null,
  ].filter(Boolean);

  return (
    <CorporateShell>
      <JsonLd data={schemas} />
      <HeroSection
        badge={t("successStory")}
        title={story.headline}
        subtitle={story.challenge}
        primaryCta={locale === "fr" ? "Obtenir un devis" : "Get a quote"}
        primaryHref={contact(loc, { intent: "quote", from: `success-stories/${slug}` })}
        secondaryCta={locale === "fr" ? "Contact" : "Contact"}
        secondaryHref={contact(loc, { from: `success-stories/${slug}` })}
        variant="light-centered"
        illustration={<HeroPhoto image={getNicheHeroImage(story.industrySlug)} />}
      />
      <section className="site-section bg-white">
        <Container size="narrow" className="space-y-8 text-muted leading-relaxed">
          {story.authorId && (
            <AuthorCard
              authorId={story.authorId}
              writtenByLabel={t("writtenBy")}
              variant="compact"
            />
          )}
          {!story.permissioned && (
            <p className="text-xs text-muted border border-primary/10 rounded-xl px-4 py-3 bg-gray-bg">
              {t("anonymizedStoryNote")}
            </p>
          )}
          <div>
            <h2 className="text-xl font-semibold text-primary">
              {locale === "fr" ? "Solution" : "Solution"}
            </h2>
            <p className="mt-3">{story.solution}</p>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-primary">
              {locale === "fr" ? "Résultat" : "Outcome"}
            </h2>
            <p className="mt-3">{story.outcome}</p>
            {showMetric && <p className="mt-2 font-medium text-primary">{story.outcomeMetric}</p>}
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
              {locale === "fr" ? "En savoir plus sur la livraison" : "Learn more about"}{" "}
              {INDUSTRY_PAGE_LABELS[story.industrySlug] ?? story.industrySlug} →
            </Link>
          </p>
        </Container>
      </section>
      <CtaSection
        title={
          locale === "fr" ? "Prêt pour des résultats similaires?" : "Ready for similar results?"
        }
        primaryLabel={locale === "fr" ? "Commencer" : "Get started"}
        primaryHref={business(loc, { from: `success-stories/${slug}` })}
        secondaryLabel={locale === "fr" ? "Nous joindre" : "Contact us"}
        secondaryHref={contact(loc)}
        variant="gradient"
      />
    </CorporateShell>
  );
}
