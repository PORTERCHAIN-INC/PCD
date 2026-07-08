import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getMessages, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { siteImages } from "@/data/site-images";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import { JsonLd } from "@/components/seo";
import {
  SERVICE_AREA_SLUGS,
  getServiceAreaMessageKey,
  isValidServiceAreaSlug,
} from "@/lib/seo/service-areas";
import { getServiceAreaContent } from "@/lib/seo/service-area-content";
import {
  buildIndustryDeliveryLinksForCityPage,
  buildIndustryPageLinksForCityPage,
} from "@/lib/seo/internal-linking";
import { buildFAQPageSchema, buildServiceSchema } from "@/lib/seo/schema";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
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
      serviceAreaLanding?: Record<string, { meta?: { title?: string; description?: string } }>;
    }
  ).serviceAreaLanding?.[key ?? ""];
  if (!area?.meta) return {};
  return buildPageMetadata(
    locale,
    `service-areas/${slug}`,
    area.meta.title ?? "",
    area.meta.description ?? ""
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

  const loc = locale as Locale;
  const businessHref = business(loc, { from: `service-areas/${slug}` });
  const contactHref = contact(loc, { from: `service-areas/${slug}` });
  const faqItems = [
    { question: area.faq.q1, answer: area.faq.a1 },
    { question: area.faq.q2, answer: area.faq.a2 },
    { question: area.faq.q3, answer: area.faq.a3 },
  ];
  const industryLinks = buildIndustryPageLinksForCityPage(loc);
  const deliveryLinks = buildIndustryDeliveryLinksForCityPage(loc, slug, messages as never);

  return (
    <CorporateShell>
      <JsonLd
        data={[
          buildFAQPageSchema(faqItems),
          buildServiceSchema({ name: area.hero.title, description: area.meta?.description }),
        ].filter(Boolean)}
      />
      <HeroSection
        badge="Service areas"
        title={area.hero.title}
        subtitle={area.hero.subtitle}
        primaryCta={area.cta.primary}
        primaryHref={businessHref}
        secondaryCta={area.cta.secondary}
        secondaryHref={contactHref}
        variant="light-centered"
        illustration={<HeroPhoto image={siteImages.hero.toronto} />}
      />
      <section className="site-section bg-white">
        <Container size="narrow">
          <h2 className="text-2xl font-semibold text-primary tracking-tight">
            {area.coverage.title}
          </h2>
          <p className="mt-4 text-muted leading-relaxed">{area.coverage.description}</p>
        </Container>
      </section>
      <FeatureSection
        label="Onboarding"
        title={area.onboarding.title}
        subtitle={area.onboarding.description}
        items={[
          { title: area.onboarding.step1Title, description: area.onboarding.step1Description },
          { title: area.onboarding.step2Title, description: area.onboarding.step2Description },
          { title: area.onboarding.step3Title, description: area.onboarding.step3Description },
        ]}
      />
      <InternalLinksBlock title="Industry delivery in this area" links={deliveryLinks} />
      <InternalLinksBlock title="Explore by industry" links={industryLinks} />
      <FaqSection title={area.faq.title} items={faqItems} />
      <CtaSection
        title={area.cta.title}
        subtitle={area.cta.description}
        primaryLabel={area.cta.primary}
        primaryHref={businessHref}
        secondaryLabel={area.cta.secondary}
        secondaryHref={contactHref}
        variant="gradient"
      />
    </CorporateShell>
  );
}
