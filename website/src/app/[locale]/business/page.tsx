import { setRequestLocale, getTranslations, getMessages } from "next-intl/server";
import SiteShell from "@/components/layout/SiteShell";
import ReviewsProof from "@/components/marketing/ReviewsProof";
import { BusinessStickyCloser } from "@/components/marketing/MarketingCloser";
import { JsonLd } from "@/components/seo";
import {
  buildFAQPageSchema,
  buildServiceSchema,
  buildSpeakableWebPageSchema,
} from "@/lib/seo/schema";
import { siteConfig } from "@/lib/seo/config";
import { business as businessRoute } from "@/lib/seo/routes";
import BusinessPageSections from "@/components/marketing/business/BusinessPageSections";
import { BUSINESS_FAQ_KEYS } from "@/data/business";
import { routing, type Locale } from "@/i18n/routing";

type Props = {
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function BusinessPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "businessPage.metadata" });
  const messages = await getMessages({ locale });
  const faqMessages = (
    messages as {
      businessPage?: {
        faq?: { items?: Record<string, { question?: string; answer?: string }> };
      };
    }
  ).businessPage?.faq;

  const faqItems = BUSINESS_FAQ_KEYS.map((key) => ({
    question: faqMessages?.items?.[key]?.question ?? "",
    answer: faqMessages?.items?.[key]?.answer ?? "",
  })).filter((item) => item.question.trim() && item.answer.trim());

  const loc = locale as Locale;
  const businessUrl = `${siteConfig.baseUrl.replace(/\/$/, "")}${businessRoute(loc)}`;

  return (
    <>
      <JsonLd
        data={[
          buildServiceSchema({
            name: t("title"),
            description: t("description"),
          }),
          buildFAQPageSchema(faqItems),
          buildSpeakableWebPageSchema({ name: t("title"), url: businessUrl }),
        ].filter(Boolean)}
      />
      <SiteShell>
        <BusinessPageSections locale={loc} />
        <ReviewsProof locale={loc} />
      </SiteShell>
      <BusinessStickyCloser />
    </>
  );
}
