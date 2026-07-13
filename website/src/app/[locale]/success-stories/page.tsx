import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { SUCCESS_STORIES } from "@/lib/seo/content/success-stories";
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
  description: "Real outcomes from merchants who partnered with Porterchain for local delivery.",
};

const EN_META = {
  title: "Merchant success stories | Porterchain",
  description:
    "How coffee roasters, pharmacies, and beauty brands scale delivery with Porterchain.",
};

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const hub = await getProgrammaticHubCopy(locale as Locale, "successStories", EN_META);
  return buildProgrammaticPageMetadata(
    locale,
    "success-stories",
    hub.title,
    hub.description,
    locale === "fr"
  );
}

export default async function SuccessStoriesHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;
  const slugs = new Set(await listLocalizedSuccessStorySlugs(loc));
  const hub = await getProgrammaticHubCopy(loc, "successStories", EN_HUB);

  const stories = SUCCESS_STORIES.filter((s) => slugs.has(s.slug));
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
