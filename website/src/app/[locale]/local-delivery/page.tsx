import type { Metadata } from "next";
import { getMessages, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { buildLocalDeliveryCityLinks } from "@/lib/seo/internal-linking";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

const PATH = "local-delivery";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const messages = await getMessages({ locale });
  const m = (messages as { localDelivery?: { meta?: { title?: string; description?: string } } })
    .localDelivery?.meta;
  return buildPageMetadata(locale, PATH, m?.title ?? "Local delivery", m?.description ?? "");
}

export default async function LocalDeliveryPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const messages = await getMessages({ locale });
  const page = (
    messages as {
      localDelivery?: {
        hero?: { title?: string; subtitle?: string };
        intro?: string;
        sections?: { heading: string; body: string }[];
      };
    }
  ).localDelivery;

  const loc = locale as Locale;

  return (
    <CorporateShell>
      <ContentClusterView
        locale={loc}
        ctaSource={PATH}
        data={{
          title: page?.hero?.title ?? "Local delivery for merchants",
          description: page?.intro ?? "",
          intro: page?.hero?.subtitle ?? page?.intro ?? "",
          sections: page?.sections,
          relatedLinks: buildLocalDeliveryCityLinks(loc),
          relatedTitle: "Local delivery by city",
        }}
      />
    </CorporateShell>
  );
}
