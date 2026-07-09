import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HeroSection from "@/components/corporate/sections/HeroSection";
import DeveloperDocsHubBody from "@/components/developers/DeveloperDocsHubBody";
import { listDeveloperDocs } from "@/lib/developer-docs";
import { getDeveloperLinks } from "@/lib/developer-links";
import { localeStaticParams } from "@/lib/seo/page-helpers";
import { portalDisplayHost } from "@/data/portal-links";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.developerDocs" });
  return {
    title: t("title"),
    description: t("description"),
    openGraph: { title: t("ogTitle"), description: t("ogDescription") },
  };
}

export default async function DeveloperDocsHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;
  const t = await getTranslations("corporate.developers.docs");
  const tBc = await getTranslations("corporate.breadcrumbs");
  const links = getDeveloperLinks();
  const apiHost = portalDisplayHost(links.openApiDocs.href);

  const hostedDocs = listDeveloperDocs().map((doc) => ({
    href: `/developers/docs/${doc.slug}`,
    title: doc.title,
    description: doc.description,
  }));

  const items = [
    {
      href: links.openApiDocs.href,
      title: t("items.openapi.title"),
      description: t("items.openapi.description", { host: apiHost }),
      external: true,
    },
    ...hostedDocs,
    {
      href: links.postman.href,
      title: t("items.postman.title"),
      description: t("items.postman.description"),
      external: true,
    },
  ];

  return (
    <CorporateShell>
      <PageBreadcrumbs
        items={[
          { label: tBc("home"), href: "/" },
          { label: tBc("developers"), href: "/developers" },
          { label: t("hero.badge") },
        ]}
      />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref={links.openApiDocs.href}
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/developers"
        variant="minimal"
      />
      <DeveloperDocsHubBody
        locale={loc}
        title={t("list.title")}
        subtitle={t("list.subtitle")}
        items={items}
      />
    </CorporateShell>
  );
}
