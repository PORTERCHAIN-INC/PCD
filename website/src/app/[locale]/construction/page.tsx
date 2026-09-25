import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import SolutionVerticalPageView from "@/components/marketing/solutions/SolutionVerticalPageView";
import { routing } from "@/i18n/routing";
import { SOLUTION_MESSAGE_KEYS } from "@/lib/solutions-hub-config";
import { buildPageMetadata } from "@/lib/seo/page-helpers";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({
    locale,
    namespace: `corporate.solutions.${SOLUTION_MESSAGE_KEYS.construction}`,
  });
  return buildPageMetadata(locale, "construction", t("meta.title"), t("meta.description"));
}

export default async function ConstructionSolutionsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <CorporateShell>
      <SolutionVerticalPageView vertical="construction" />
    </CorporateShell>
  );
}
