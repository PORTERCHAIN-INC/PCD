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
  const t = await getTranslations({ locale, namespace: "corporate.metadata.securityOverview" });
  return trustScaffoldMetadata(locale, "trust/security", t("title"), t("description"));
}

export default async function SecurityOverviewPage({ params }: Props) {
  const { locale } = await params;
  const t = await getTranslations({
    locale,
    namespace: "corporate.trustScaffolds.securityOverview",
  });
  return (
    <TrustScaffoldPage
      locale={locale}
      pathSegment="trust/security"
      title={t("title")}
      description={t("description")}
      body={t("body")}
      breadcrumbLabel={t("breadcrumb")}
    />
  );
}
