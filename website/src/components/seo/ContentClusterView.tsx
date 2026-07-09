import Container from "@/components/ui/Container";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { getPageHeroImage } from "@/data/site-images";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import PlatformBridgeSection from "@/components/seo/PlatformBridgeSection";
import PageBreadcrumbs, { type BreadcrumbItem } from "@/components/seo/PageBreadcrumbs";
import { JsonLd } from "@/components/seo";
import { buildFAQPageSchema } from "@/lib/seo/schema";
import type { Locale } from "@/i18n/routing";
import { demoContact } from "@/lib/seo/routes";

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
}

export default function ContentClusterView({
  locale,
  data,
  ctaSource,
  breadcrumbs,
}: ContentClusterViewProps) {
  const demoHref = demoContact(locale, ctaSource);
  const faqItems = data.items ?? [];
  const faqSchema = buildFAQPageSchema(faqItems);

  return (
    <>
      {faqSchema && <JsonLd data={faqSchema} />}
      {breadcrumbs && breadcrumbs.length > 0 && <PageBreadcrumbs items={breadcrumbs} />}
      <HeroSection
        badge="Porterchain"
        title={data.title}
        subtitle={data.intro}
        primaryCta="Get a quote"
        primaryHref={demoHref}
        secondaryCta="See vehicles"
        secondaryHref="/business#fleet"
        variant="light-centered"
        illustration={<HeroPhoto image={getPageHeroImage(ctaSource)} />}
        trackSource={ctaSource}
      />
      <PlatformBridgeSection from={ctaSource} />

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
            <div className="overflow-x-auto">
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

      {faqItems.length > 0 && <FaqSection title="Frequently asked questions" items={faqItems} />}

      {data.relatedLinks && data.relatedLinks.length > 0 && (
        <InternalLinksBlock
          title={data.relatedTitle ?? "Related pages"}
          links={data.relatedLinks}
        />
      )}

      <CtaSection
        title="Ready for transportation capacity on your lanes?"
        subtitle="Tell us what needs to move. We'll quote the right vehicle-and-driver capacity for your operation."
        primaryLabel="Get a quote"
        primaryHref={demoHref}
        secondaryLabel="See vehicles"
        secondaryHref="/business#fleet"
        variant="gradient"
        trackSource={ctaSource}
      />
    </>
  );
}
