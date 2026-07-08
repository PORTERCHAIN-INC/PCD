import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { SERVICE_AREA_SLUGS } from "@/lib/seo/service-areas";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { serviceAreaSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "service-areas",
    "Service areas | Porterchain local delivery",
    "Same-day and recurring delivery across Toronto, the GTA, Kitchener-Waterloo, London, Niagara, and Ontario metros."
  );
}

export default async function ServiceAreasHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title="Service areas"
        description="Local courier and delivery coverage across Ontario metros we know well."
        items={SERVICE_AREA_SLUGS.map((slug) => ({
          href: serviceAreaSlug(loc, slug),
          title: slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
          description: `Recurring and same-day delivery in ${slug.replace(/-/g, " ")}.`,
        }))}
        ctaSource="service-areas"
      />
    </CorporateShell>
  );
}
