import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import Container from "@/components/ui/Container";
import { buildPageMetadata } from "@/lib/seo/page-helpers";

type TrustScaffoldProps = {
  locale: string;
  pathSegment: string;
  title: string;
  description: string;
  body: string;
  breadcrumbLabel: string;
};

export function trustScaffoldMetadata(
  locale: string,
  pathSegment: string,
  title: string,
  description: string
): Metadata {
  return buildPageMetadata(locale, pathSegment, title, description, { index: false });
}

export default async function TrustScaffoldPage({
  locale,
  pathSegment,
  title,
  description,
  body,
  breadcrumbLabel,
}: TrustScaffoldProps) {
  setRequestLocale(locale);
  const tBc = await getTranslations("corporate.breadcrumbs");

  return (
    <CorporateShell>
      <PageBreadcrumbs
        items={[
          { label: tBc("home"), href: "/" },
          { label: tBc("trust"), href: "/trust" },
          { label: breadcrumbLabel },
        ]}
      />
      <section className="site-section bg-white">
        <Container className="max-w-3xl">
          <h1 className="text-3xl font-bold text-primary">{title}</h1>
          <p className="mt-4 text-muted">{description}</p>
          <div className="prose prose-sm mt-8 max-w-none text-muted whitespace-pre-wrap">
            {body}
          </div>
        </Container>
      </section>
    </CorporateShell>
  );
}
