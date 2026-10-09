import type { ReactNode } from "react";
import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import MarketingHero from "@/components/marketing/MarketingHero";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { getPageHeroImage } from "@/data/site-images";
import MarketingFaq from "@/components/marketing/MarketingFaq";
import MarketingCloser from "@/components/marketing/MarketingCloser";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import PageBreadcrumbs, { type BreadcrumbItem } from "@/components/seo/PageBreadcrumbs";
import { JsonLd } from "@/components/seo";
import { buildFAQPageSchema, buildServiceSchema } from "@/lib/seo/schema";
import type { Locale } from "@/i18n/routing";
import { quoteContact } from "@/lib/seo/routes";
import PlatformBridgeSection from "@/components/seo/PlatformBridgeSection";

export type ContentClusterData = {
  title: string;
  description: string;
  intro: string;
  items?: { question: string; answer: string }[];
  sections?: { heading: string; body: string }[];
  comparisonRows?: {
    dimension: string;
    porterchain: string;
    alternative: string;
    alternativeLabel?: string;
  }[];
  alternativeLabel?: string;
  relatedLinks?: { href: string; label: string }[];
  relatedTitle?: string;
};

interface ContentClusterViewProps {
  locale: Locale;
  data: ContentClusterData;
  ctaSource: string;
  breadcrumbs?: BreadcrumbItem[];
  secondaryCta?: string;
  secondaryHref?: string;
  topNav?: ReactNode;
}

export default async function ContentClusterView({
  locale,
  data,
  ctaSource,
  breadcrumbs,
  secondaryCta = "See vehicles",
  secondaryHref = "/vehicles",
  topNav,
}: ContentClusterViewProps) {
  const tCta = await getTranslations("common.cta");
  const tSeo = await getTranslations("corporate.seo.sectionLabels");
  const quoteLabel = tCta("quote");
  const quoteHref = quoteContact(locale, ctaSource);
  const faqItems = data.items ?? [];
  const faqSchema = buildFAQPageSchema(faqItems);
  const serviceSchema =
    faqItems.length > 0
      ? buildServiceSchema({ name: data.title, description: data.description })
      : null;
  const secondaryLabel = secondaryCta === "See vehicles" ? tSeo("seeVehicles") : secondaryCta;

  return (
    <>
      <JsonLd data={[faqSchema, serviceSchema].filter(Boolean)} />
      {breadcrumbs && breadcrumbs.length > 0 && <PageBreadcrumbs items={breadcrumbs} />}
      {topNav}
      <MarketingHero
        badge="Porterchain"
        title={data.title}
        subtitle={data.intro}
        primaryCta={quoteLabel}
        primaryHref={quoteHref}
        secondaryCta={secondaryLabel}
        secondaryHref={secondaryHref}
        variant="light-centered"
        illustration={<HeroPhoto image={getPageHeroImage(ctaSource)} />}
        trackSource={ctaSource}
      />

      {faqItems.length > 0 && <MarketingFaq title={tSeo("faqTitle")} items={faqItems} />}

      {data.sections?.map((section) => (
        <section key={section.heading} className="site-section bg-white">
          <Container size="narrow">
            <h2 className="text-2xl font-semibold text-primary tracking-tight">
              {section.heading}
            </h2>
            <div className="mt-4 space-y-4 text-muted leading-relaxed">
              {section.body.split("\n\n").map((para) => (
                <p key={para.slice(0, 40)}>{para}</p>
              ))}
            </div>
          </Container>
        </section>
      ))}

      {data.comparisonRows && data.comparisonRows.length > 0 && (
        <section className="site-section bg-gray-bg">
          <Container>
            <div
              className="overflow-x-auto"
              tabIndex={0}
              role="region"
              aria-label="Scrollable table"
            >
              <table className="w-full min-w-[640px] text-left border-collapse">
                <thead>
                  <tr className="border-b border-primary/10">
                    <th className="py-3 pr-4 text-sm font-semibold text-primary">Dimension</th>
                    <th className="py-3 pr-4 text-sm font-semibold text-primary">Porterchain</th>
                    <th className="py-3 text-sm font-semibold text-primary">
                      {data.alternativeLabel ?? "Alternative"}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.comparisonRows.map((row) => (
                    <tr key={row.dimension} className="border-b border-primary/5 align-top">
                      <td className="py-4 pr-4 font-medium text-primary">{row.dimension}</td>
                      <td className="py-4 pr-4 text-muted">{row.porterchain}</td>
                      <td className="py-4 text-muted">{row.alternative}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Container>
        </section>
      )}

      {data.relatedLinks && data.relatedLinks.length > 0 && (
        <InternalLinksBlock
          title={data.relatedTitle ?? "Related pages"}
          links={data.relatedLinks}
        />
      )}

      <PlatformBridgeSection from={ctaSource} />
      <MarketingCloser
        title={tSeo("readyForCapacityTitle")}
        subtitle={tSeo("readyForCapacitySubtitle")}
        primaryLabel={quoteLabel}
        primaryHref={quoteHref}
        secondaryLabel={tSeo("seeVehicles")}
        secondaryHref="/business#fleet"
        variant="gradient"
        trackSource={ctaSource}
      />
    </>
  );
}
