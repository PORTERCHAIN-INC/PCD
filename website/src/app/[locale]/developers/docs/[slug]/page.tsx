import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import Container from "@/components/ui/Container";
import MarkdownContent from "@/components/blog/MarkdownContent";
import LinkButton from "@/components/marketing/corporate/ui/LinkButton";
import {
  DEVELOPER_DOC_SLUGS,
  getDeveloperDoc,
  isValidDeveloperDocSlug,
} from "@/lib/developer-docs";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { ensureStaticParams } from "@/lib/seo/ensure-static-params";
import { routing } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    for (const slug of DEVELOPER_DOC_SLUGS) {
      if (getDeveloperDoc(slug)) {
        params.push({ locale, slug });
      }
    }
  }
  return ensureStaticParams(params, { locale: routing.locales[0]!, slug: "partner-guide" });
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!isValidDeveloperDocSlug(slug)) return {};
  const doc = getDeveloperDoc(slug);
  if (!doc) return {};
  return buildPageMetadata(
    locale,
    `developers/docs/${slug}`,
    `${doc.title} | Porterchain Developers`,
    doc.description
  );
}

export default async function DeveloperDocPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  if (!isValidDeveloperDocSlug(slug)) notFound();

  const doc = getDeveloperDoc(slug);
  if (!doc) notFound();

  const t = await getTranslations("corporate.developers.docs");
  const tBc = await getTranslations("corporate.breadcrumbs");

  return (
    <CorporateShell>
      <PageBreadcrumbs
        items={[
          { label: tBc("home"), href: "/" },
          { label: tBc("developers"), href: "/developers" },
          { label: t("hero.badge"), href: "/developers/docs" },
          { label: doc.title },
        ]}
      />
      <section className="site-section bg-white">
        <Container className="max-w-3xl">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-8">
            <div>
              <p className="text-sm font-medium text-secondary">{t("article.label")}</p>
              <h1 className="mt-2 text-3xl font-semibold text-primary">{doc.title}</h1>
              <p className="mt-3 text-muted leading-relaxed">{doc.description}</p>
            </div>
            <LinkButton href={doc.githubHref} variant="outline" external>
              {t("article.githubMirror")}
            </LinkButton>
          </div>
          <MarkdownContent content={doc.content} />
        </Container>
      </section>
    </CorporateShell>
  );
}
