import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { listPublicSuccessStories } from "@/lib/seo/content/success-stories";
import {
  getLocalizedSuccessStory,
  getProgrammaticHubCopy,
  listLocalizedSuccessStorySlugs,
} from "@/lib/seo/programmatic-content";
import { localeStaticParams, buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import { successStorySlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

const EN_HUB = {
  title: "Success stories",
  description: "Permissioned merchant outcomes from Porterchain capacity partnerships.",
};

const EN_META = {
  title: "Merchant success stories | Porterchain",
  description:
    "How GTA merchants use Porterchain vehicle-and-driver capacity — stories published with customer approval.",
};

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const hub = await getProgrammaticHubCopy(locale as Locale, "successStories", EN_META);
  const publicCount = (await listLocalizedSuccessStorySlugs(locale as Locale)).length;
  const meta = buildProgrammaticPageMetadata(
    locale,
    "success-stories",
    hub.title,
    hub.description,
    locale === "fr"
  );
  // Noindex empty hub until more permissioned stories ship.
  if (publicCount === 0) {
    return { ...meta, robots: { index: false, follow: true } };
  }
  return meta;
}

export default async function SuccessStoriesHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;
  const slugs = new Set(await listLocalizedSuccessStorySlugs(loc));
  const hub = await getProgrammaticHubCopy(loc, "successStories", EN_HUB);

  const stories = listPublicSuccessStories().filter((s) => slugs.has(s.slug));
  const items = await Promise.all(
    stories.map(async (s) => {
      const story = (await getLocalizedSuccessStory(loc, s.slug))!;
      return {
        href: successStorySlug(loc, s.slug),
        title: story.title,
        description: story.description,
      };
    })
  );

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title={hub.title}
        description={hub.description}
        items={items}
        ctaSource="success-stories"
      />
    </CorporateShell>
  );
}
