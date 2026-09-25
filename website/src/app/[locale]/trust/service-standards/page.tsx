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
  const t = await getTranslations({ locale, namespace: "corporate.metadata.serviceStandards" });
  return trustScaffoldMetadata(locale, "trust/service-standards", t("title"), t("description"));
}

export default async function Page({ params }: Props) {
  const { locale } = await params;
  const t = await getTranslations({
    locale,
    namespace: "corporate.trustScaffolds.serviceStandards",
  });
  return (
    <TrustScaffoldPage
      locale={locale}
      pathSegment="trust/service-standards"
      title={t("title")}
      description={t("description")}
      body={t("body")}
      breadcrumbLabel={t("breadcrumb")}
    />
  );
}
