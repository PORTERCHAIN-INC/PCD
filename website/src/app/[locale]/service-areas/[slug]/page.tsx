import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import MarketingHero from "@/components/marketing/MarketingHero";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { siteImages } from "@/data/site-images";
import FeatureSection from "@/components/marketing/corporate/sections/FeatureSection";
import MarketingFaq from "@/components/marketing/MarketingFaq";
import MarketingCloser from "@/components/marketing/MarketingCloser";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import { JsonLd } from "@/components/seo";
import FadeIn from "@/components/marketing/corporate/motion/FadeIn";
import {
  SERVICE_AREA_SLUGS,
  getServiceAreaMessageKey,
  isCoreServiceArea,
  isValidServiceAreaSlug,
} from "@/lib/seo/service-areas";
import {
  getServiceAreaContent,
  isPublishableServiceArea,
  type ServiceAreaMessageContent,
} from "@/lib/seo/service-area-content";
import {
  buildIndustryDeliveryLinksForCityPage,
  buildIndustryPageLinksForCityPage,
  buildIntentHubLinks,
  INTENT_HUB_FAQ_SLUGS,
} from "@/lib/seo/internal-linking";
import { getLocalizedFaqCluster } from "@/lib/seo/programmatic-content";
import { buildFAQPageSchema, buildServiceSchema } from "@/lib/seo/schema";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { collectNicheFaqItems } from "@/lib/seo/niche-personas";
import { getCityNeighbourhoods, getCityPostalCodes } from "@/lib/seo/city-neighbourhoods";
import PostalCoverageChecker from "@/components/seo/PostalCoverageChecker";
import { business, contact } from "@/lib/seo/routes";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    for (const slug of SERVICE_AREA_SLUGS) {
      params.push({ locale, slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!isValidServiceAreaSlug(slug)) return {};
  const messages = await getMessages({ locale });
  const key = getServiceAreaMessageKey(slug);
  const area = (
    messages as {
      serviceAreaLanding?: Record<string, ServiceAreaMessageContent>;
    }
  ).serviceAreaLanding?.[key ?? ""];
  if (!area?.meta) return {};
  const publishable = isPublishableServiceArea(area);
  const indexable = publishable && isCoreServiceArea(slug);
  return buildPageMetadata(
    locale,
    `service-areas/${slug}`,
    area.meta.title ?? "",
    area.meta.description ?? "",
    { index: indexable }
  );
}

export default async function ServiceAreaPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  if (!isValidServiceAreaSlug(slug)) notFound();

  const key = getServiceAreaMessageKey(slug);
  if (!key) notFound();

  const area = await getServiceAreaContent(locale, key);
  if (!area) notFound();

  const messages = await getMessages({ locale });
  const tSeo = await getTranslations("corporate.seo.sectionLabels");
  const tCta = await getTranslations("common.cta");
  const quoteLabel = tCta("quote");

  const loc = locale as Locale;
  const quoteHref = contact(loc, { intent: "quote", from: `service-areas/${slug}` });
  const businessHref = business(loc, { from: `service-areas/${slug}` });
  const serviceAreaBadge = isCoreServiceArea(slug)
    ? `${tSeo("serviceAreas")} · ${tSeo("coreServiceArea")}`
    : `${tSeo("serviceAreas")} · ${tSeo("availableByConfirmation")}`;
  const faqItems = [
    ...collectNicheFaqItems(area.faq),
    { question: tSeo("pricingFaqQ"), answer: tSeo("pricingFaqA") },
  ];
  const hasPriceSignal = /quote-based|written quote|sur devis|devis écrit/i.test(
    area.hero.subtitle
  );
  const heroSubtitle = hasPriceSignal
    ? area.hero.subtitle
    : locale === "fr"
      ? `${area.hero.subtitle} Capacité sur devis — demandez un devis écrit.`
      : `${area.hero.subtitle} Quote-based capacity — request a written quote.`;
  const industryLinks = buildIndustryPageLinksForCityPage(loc);
  const deliveryLinks = buildIndustryDeliveryLinksForCityPage(loc, slug, messages as never);
  const titleBySlug: Partial<Record<(typeof INTENT_HUB_FAQ_SLUGS)[number], string>> = {};
  for (const intentSlug of INTENT_HUB_FAQ_SLUGS) {
    const cluster = await getLocalizedFaqCluster(loc, intentSlug);
    if (cluster) titleBySlug[intentSlug] = cluster.title;
  }
  const intentLinks = buildIntentHubLinks(loc, `service-areas/${slug}`, titleBySlug);
  const solutionBullets = area.solution
    ? [area.solution.bullet1, area.solution.bullet2, area.solution.bullet3].filter(
        (b): b is string => Boolean(b)
      )
    : [];
  const neighbourhoods = getCityNeighbourhoods(slug);
  const postalCodes = getCityPostalCodes(slug);

  return (
    <CorporateShell>
      <JsonLd
        data={[
          buildFAQPageSchema(faqItems),
          buildServiceSchema({
            name: area.hero.title,
            description: area.meta?.description,
            geoSlug: slug,
            postalCodes: postalCodes.length ? postalCodes : undefined,
          }),
        ].filter(Boolean)}
      />
      <MarketingHero
        badge={serviceAreaBadge}
        title={area.hero.title}
        subtitle={heroSubtitle}
        primaryCta={quoteLabel}
        primaryHref={quoteHref}
        secondaryCta={area.cta.secondary}
        secondaryHref={businessHref}
        variant="light-centered"
        clearNav
        illustration={<HeroPhoto image={siteImages.hero.toronto} />}
      />
      {area.painPoints && (
        <FeatureSection
          label={tSeo("painPoints")}
          title={area.painPoints.title}
          items={[
            { title: area.painPoints.item1, description: "" },
            { title: area.painPoints.item2, description: "" },
            { title: area.painPoints.item3, description: "" },
          ]}
        />
      )}
      {area.solution && (
        <FeatureSection
          label={tSeo("solution")}
          title={area.solution.title}
          subtitle={area.solution.description}
          items={solutionBullets.map((b) => ({ title: b, description: "" }))}
        />
      )}
      <section className="site-section bg-white">
        <Container size="narrow">
          <h2 className="text-2xl font-semibold text-primary tracking-tight">
            {area.coverage.title}
          </h2>
          <p className="mt-4 text-muted leading-relaxed">{area.coverage.description}</p>
          {neighbourhoods.length > 0 && (
            <div className="mt-8">
              <h3 className="text-lg font-semibold text-primary">
                {tSeo("neighbourhoodCoverage")}
              </h3>
              <ul className="mt-4 grid gap-3 sm:grid-cols-2">
                {neighbourhoods.map((n) => (
                  <li key={n.name} className="text-sm text-muted">
                    <span className="font-medium text-primary">{n.name}</span>
                    <span className="block mt-0.5 text-xs">
                      {tSeo("fsaPrefixes")}: {n.fsaPrefixes.join(", ")}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-xs text-muted">{tSeo("neighbourhoodCoverageNote")}</p>
            </div>
          )}
          <div className="mt-10">
            <PostalCoverageChecker
              locale={loc}
              cityLabel={area.hero.title
                .replace(/^Delivery in /i, "")
                .replace(/^Livraison à /i, "")}
              trackSource={`service-areas/${slug}`}
            />
          </div>
        </Container>
      </section>
      {area.workflow && (
        <FeatureSection
          label={tSeo("workflow")}
          title={area.workflow.title}
          subtitle={area.workflow.description}
          items={[
            { title: area.workflow.step1Title, description: area.workflow.step1Description },
            { title: area.workflow.step2Title, description: area.workflow.step2Description },
            { title: area.workflow.step3Title, description: area.workflow.step3Description },
          ]}
        />
      )}
      {area.vehicles && (
        <section className="site-section bg-gray-bg">
          <Container size="narrow">
            <FadeIn>
              <h2 className="text-2xl font-semibold text-primary tracking-tight">
                {area.vehicles.title}
              </h2>
              <p className="mt-4 text-muted leading-relaxed">{area.vehicles.description}</p>
            </FadeIn>
          </Container>
        </section>
      )}
      <FeatureSection
        label={tSeo("onboarding")}
        title={area.onboarding.title}
        subtitle={area.onboarding.description}
        items={[
          { title: area.onboarding.step1Title, description: area.onboarding.step1Description },
          { title: area.onboarding.step2Title, description: area.onboarding.step2Description },
          { title: area.onboarding.step3Title, description: area.onboarding.step3Description },
        ]}
      />
      <InternalLinksBlock
        title={tSeo("relatedPages")}
        links={[...deliveryLinks, ...industryLinks, ...intentLinks].filter(
          (link, index, all) => all.findIndex((item) => item.href === link.href) === index
        )}
      />
      <MarketingFaq title={area.faq.title} items={faqItems} />
      <MarketingCloser
        title={area.cta.title}
        subtitle={area.cta.description}
        primaryLabel={quoteLabel}
        primaryHref={quoteHref}
        secondaryLabel={area.cta.secondary}
        secondaryHref={businessHref}
        variant="gradient"
      />
    </CorporateShell>
  );
}
