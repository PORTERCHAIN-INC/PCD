import type { Metadata } from "next";
import { getMessages, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const messages = await getMessages({ locale });
  const m = (messages as { integrations?: { meta?: { title?: string; description?: string } } })
    .integrations?.meta;
  return buildPageMetadata(
    locale,
    "integrations",
    m?.title ?? "Integrations",
    m?.description ?? ""
  );
}

export default async function IntegrationsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const messages = await getMessages({ locale });
  const page = (
    messages as {
      integrations?: {
        hero?: { title?: string; subtitle?: string };
        intro?: string;
        sections?: { heading: string; body: string }[];
      };
    }
  ).integrations;

  return (
    <CorporateShell>
      <ContentClusterView
        locale={locale as Locale}
        ctaSource="integrations"
        data={{
          title: page?.hero?.title ?? "Integrations",
          description: page?.intro ?? "",
          intro: page?.hero?.subtitle ?? page?.intro ?? "",
          sections: page?.sections,
        }}
      />
    </CorporateShell>
  );
}
