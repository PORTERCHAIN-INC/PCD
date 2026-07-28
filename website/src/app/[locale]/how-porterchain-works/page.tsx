import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HowPorterchainWorksView from "@/components/how-it-works/HowPorterchainWorksView";
import { JsonLd } from "@/components/seo";
import { buildHowToSchema, buildOrganizationSchema } from "@/lib/seo/schema";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";
import { collectTimelineSteps } from "@/lib/corporate-content";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

const SLUG = "how-porterchain-works";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({
    locale,
    namespace: "corporate.metadata.howPorterchainWorks",
  });
  return buildPageMetadata(locale, SLUG, t("title"), t("description"));
}

export default async function HowPorterchainWorksPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.howPorterchainWorks");
  const steps = collectTimelineSteps(t, "steps.items", 4);

  return (
    <CorporateShell>
      <JsonLd
        data={[
          buildOrganizationSchema(),
          buildHowToSchema({
            name: t("steps.title"),
            description: t("steps.subtitle"),
            steps: steps.map((step) => ({
              name: step.title,
              text: step.description,
            })),
          }),
        ].filter(Boolean)}
      />
      <HowPorterchainWorksView locale={locale as Locale} />
    </CorporateShell>
  );
}
