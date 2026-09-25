import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { routing } from "@/i18n/routing";
import TrustScaffoldPage, {
  trustScaffoldMetadata,
} from "@/components/marketing/trust/TrustScaffoldPage";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.corrections" });
  return trustScaffoldMetadata(locale, "trust/corrections", t("title"), t("description"));
}

export default async function CorrectionsPage({ params }: Props) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.trustScaffolds.corrections" });
  return (
    <TrustScaffoldPage
      locale={locale}
      pathSegment="trust/corrections"
      title={t("title")}
      description={t("description")}
      body={t("body")}
      breadcrumbLabel={t("breadcrumb")}
    />
  );
}
