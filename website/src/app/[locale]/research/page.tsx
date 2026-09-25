import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import Container from "@/components/ui/Container";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { RESEARCH_REPORTS, getIndexableResearchReports } from "@/lib/seo/content/research";
import { JsonLd } from "@/components/seo";
import { buildDatasetSchema } from "@/lib/seo/schema";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.researchHub" });
  return buildPageMetadata(locale, "research", t("title"), t("description"), { index: false });
}

export default async function ResearchHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.researchHub");
  const tBc = await getTranslations("corporate.breadcrumbs");
  const publishedDatasets = getIndexableResearchReports().map((report) =>
    buildDatasetSchema({
      name: report.title,
      description: report.description,
      keywords: ["logistics", "GTA", "B2B delivery", report.slug],
    })
  );

  return (
    <CorporateShell>
      {publishedDatasets.length > 0 ? <JsonLd data={publishedDatasets} /> : null}
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: t("breadcrumb") }]} />
      <section className="site-section bg-white">
        <Container className="max-w-3xl">
          <h1 className="text-3xl font-bold text-primary">{t("title")}</h1>
          <p className="mt-4 text-muted">{t("description")}</p>
          <ul className="mt-8 space-y-6">
            {RESEARCH_REPORTS.map((report) => (
              <li key={report.slug} className="rounded-xl border border-primary/10 p-6">
                <h2 className="text-lg font-semibold text-primary">{report.title}</h2>
                <p className="mt-2 text-sm text-muted">{report.description}</p>
                <p className="mt-3 text-xs uppercase tracking-wide text-muted">{t("draftLabel")}</p>
              </li>
            ))}
          </ul>
        </Container>
      </section>
    </CorporateShell>
  );
}
