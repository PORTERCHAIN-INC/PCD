import { getTranslations } from "next-intl/server";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import type { Locale } from "@/i18n/routing";
import { buildIntentHubLinks, INTENT_HUB_FAQ_SLUGS } from "@/lib/seo/internal-linking";
import { getLocalizedFaqCluster } from "@/lib/seo/programmatic-content";

type Props = {
  locale: Locale;
};

export default async function BusinessIntentGuides({ locale }: Props) {
  const titleBySlug: Partial<Record<(typeof INTENT_HUB_FAQ_SLUGS)[number], string>> = {};
  for (const slug of INTENT_HUB_FAQ_SLUGS) {
    const cluster = await getLocalizedFaqCluster(locale, slug);
    if (cluster) titleBySlug[slug] = cluster.title;
  }

  const links = buildIntentHubLinks(locale, "business", titleBySlug);
  const t = await getTranslations("corporate.seo.sectionLabels");

  return <InternalLinksBlock title={t("intentGuides")} links={links} />;
}
