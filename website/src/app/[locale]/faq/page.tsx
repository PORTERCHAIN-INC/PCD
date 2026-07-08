import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getMessages, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { FAQ_CLUSTERS } from "@/lib/seo/content/faq-clusters";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { faqSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "faq",
    "Delivery FAQ for merchants | Porterchain",
    "Answers about pricing, onboarding, CSV uploads, API integrations, service areas, and industry-specific delivery."
  );
}

export default async function FaqHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;

  const items = FAQ_CLUSTERS.map((c) => ({
    href: faqSlug(loc, c.slug),
    title: c.title,
    description: c.description,
  }));

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title="Frequently asked questions"
        description="Practical answers about merchant delivery, pricing, onboarding, and local service areas across the GTA and Ontario."
        items={items}
        ctaSource="faq"
      />
    </CorporateShell>
  );
}
