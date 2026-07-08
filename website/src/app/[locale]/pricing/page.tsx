import type { Metadata } from "next";
import { getMessages, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

async function pillarMetadata(locale: string, path: string, ns: string): Promise<Metadata> {
  const messages = await getMessages({ locale });
  const m = (messages as Record<string, { meta?: { title?: string; description?: string } }>)[ns]
    ?.meta;
  return buildPageMetadata(locale, path, m?.title ?? path, m?.description ?? "");
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pillarMetadata(locale, "pricing", "pricing");
}

export default async function PricingPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const messages = await getMessages({ locale });
  const page = (
    messages as {
      pricing?: {
        hero?: { title?: string; subtitle?: string };
        intro?: string;
        sections?: { heading: string; body: string }[];
      };
    }
  ).pricing;

  return (
    <CorporateShell>
      <ContentClusterView
        locale={locale as Locale}
        ctaSource="pricing"
        data={{
          title: page?.hero?.title ?? "Pricing",
          description: page?.intro ?? "",
          intro: page?.hero?.subtitle ?? page?.intro ?? "",
          sections: page?.sections,
        }}
      />
    </CorporateShell>
  );
}
