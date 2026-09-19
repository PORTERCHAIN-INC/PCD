import type { Locale } from "@/i18n/routing";
import type { ComparisonPage } from "./content/comparison-pages";
import { getComparisonBySlug } from "./content/comparison-pages";
import type { FAQCluster } from "./content/faq-clusters";
import { getFaqClusterBySlug } from "./content/faq-clusters";
import type { AuthorityPage } from "./content/authority-pages";
import { getAuthorityPageBySlug } from "./content/authority-pages";
import type { SuccessStory } from "./content/success-stories";
import { getSuccessStoryBySlug } from "./content/success-stories";
import type { CapabilityPage } from "./content/capabilities";
import { getCapabilityBySlug } from "./content/capabilities";

type FrCompareOverride = Pick<
  ComparisonPage,
  "title" | "description" | "intro" | "alternativeLabel" | "comparisonRows" | "extraLinks"
>;

type FrFaqOverride = Pick<FAQCluster, "title" | "description" | "intro" | "items"> & {
  extraLinks?: FAQCluster["extraLinks"];
};

type FrGuideOverride = Pick<AuthorityPage, "title" | "description" | "intro" | "sections"> & {
  extraLinks?: AuthorityPage["extraLinks"];
};

type FrSuccessOverride = Pick<
  SuccessStory,
  | "title"
  | "description"
  | "headline"
  | "challenge"
  | "solution"
  | "outcome"
  | "quote"
  | "quoteAttribution"
  | "outcomeMetric"
>;

type FrCapabilityOverride = Pick<CapabilityPage, "title" | "description" | "intro" | "sections"> & {
  extraLinks?: CapabilityPage["extraLinks"];
};

type SeoProgrammaticFr = {
  hubs?: {
    compare?: { title: string; description: string };
    faq?: { title: string; description: string };
    guides?: { title: string; description: string };
    successStories?: { title: string; description: string };
    capabilities?: { title: string; description: string };
  };
  compare?: Record<string, FrCompareOverride>;
  faq?: Record<string, FrFaqOverride>;
  guides?: Record<string, FrGuideOverride>;
  successStories?: Record<string, FrSuccessOverride>;
  capabilities?: Record<string, FrCapabilityOverride>;
};

let frCache: SeoProgrammaticFr | null = null;

async function loadFrProgrammatic(): Promise<SeoProgrammaticFr> {
  if (!frCache) {
    frCache = (await import("../../../messages/seo-programmatic-fr.json"))
      .default as SeoProgrammaticFr;
  }
  return frCache;
}

export async function hasProgrammaticLocale(
  locale: string,
  namespace: keyof Pick<
    SeoProgrammaticFr,
    "compare" | "faq" | "guides" | "successStories" | "capabilities"
  >,
  slug: string
): Promise<boolean> {
  if (locale === "en") return true;
  const fr = await loadFrProgrammatic();
  return Boolean(fr[namespace]?.[slug]);
}

export async function getLocalizedComparison(
  locale: Locale,
  slug: string
): Promise<ComparisonPage | null> {
  const en = getComparisonBySlug(slug);
  if (!en) return null;
  if (locale === "en") return en;
  const fr = (await loadFrProgrammatic()).compare?.[slug];
  if (!fr) return null;
  return {
    ...en,
    ...fr,
    comparisonRows: fr.comparisonRows ?? en.comparisonRows,
    extraLinks: fr.extraLinks ?? en.extraLinks,
  };
}

export async function getLocalizedFaqCluster(
  locale: Locale,
  slug: string
): Promise<FAQCluster | null> {
  const en = getFaqClusterBySlug(slug);
  if (!en) return null;
  if (locale === "en") return en;
  const fr = (await loadFrProgrammatic()).faq?.[slug];
  if (!fr) return null;
  return {
    ...en,
    ...fr,
    items: fr.items ?? en.items,
    extraLinks: fr.extraLinks ?? en.extraLinks,
  };
}

export async function getLocalizedAuthorityPage(
  locale: Locale,
  slug: string
): Promise<AuthorityPage | null> {
  const en = getAuthorityPageBySlug(slug);
  if (!en) return null;
  if (locale === "en") return en;
  const fr = (await loadFrProgrammatic()).guides?.[slug];
  if (!fr) return null;
  return {
    ...en,
    ...fr,
    sections: fr.sections ?? en.sections,
    extraLinks: fr.extraLinks ?? en.extraLinks,
  };
}

export async function getLocalizedSuccessStory(
  locale: Locale,
  slug: string
): Promise<SuccessStory | null> {
  const en = getSuccessStoryBySlug(slug);
  if (!en) return null;
  if (locale === "en") return en;
  const fr = (await loadFrProgrammatic()).successStories?.[slug];
  if (!fr) return null;
  return { ...en, ...fr };
}

export async function getProgrammaticHubCopy(
  locale: Locale,
  hub: keyof NonNullable<SeoProgrammaticFr["hubs"]>,
  en: { title: string; description: string }
): Promise<{ title: string; description: string }> {
  if (locale === "en") return en;
  const fr = (await loadFrProgrammatic()).hubs?.[hub];
  return fr ?? en;
}

export async function listLocalizedComparisonSlugs(locale: Locale): Promise<string[]> {
  const { COMPARISON_PAGES } = await import("./content/comparison-pages");
  if (locale === "en") return COMPARISON_PAGES.map((p) => p.slug);
  const fr = await loadFrProgrammatic();
  return COMPARISON_PAGES.map((p) => p.slug).filter((slug) => Boolean(fr.compare?.[slug]));
}

export async function listLocalizedFaqSlugs(locale: Locale): Promise<string[]> {
  const { FAQ_CLUSTERS } = await import("./content/faq-clusters");
  if (locale === "en") return FAQ_CLUSTERS.map((c) => c.slug);
  const fr = await loadFrProgrammatic();
  return FAQ_CLUSTERS.map((c) => c.slug).filter((slug) => Boolean(fr.faq?.[slug]));
}

const GUIDE_SLUGS_EXCLUDING_CANONICAL = async () => {
  const { AUTHORITY_PAGES } = await import("./content/authority-pages");
  return AUTHORITY_PAGES.filter((p) => p.slug !== "how-porterchain-works").map((p) => p.slug);
};

export async function listLocalizedGuideSlugs(locale: Locale): Promise<string[]> {
  const slugs = await GUIDE_SLUGS_EXCLUDING_CANONICAL();
  if (locale === "en") return slugs;
  const fr = await loadFrProgrammatic();
  return slugs.filter((slug) => Boolean(fr.guides?.[slug]));
}

export async function listLocalizedSuccessStorySlugs(locale: Locale): Promise<string[]> {
  const { SUCCESS_STORIES } = await import("./content/success-stories");
  if (locale === "en") return SUCCESS_STORIES.map((s) => s.slug);
  const fr = await loadFrProgrammatic();
  return SUCCESS_STORIES.map((s) => s.slug).filter((slug) => Boolean(fr.successStories?.[slug]));
}

export async function getLocalizedCapability(
  locale: Locale,
  slug: string
): Promise<CapabilityPage | null> {
  const en = getCapabilityBySlug(slug);
  if (!en) return null;
  if (locale === "en") return en;
  const fr = (await loadFrProgrammatic()).capabilities?.[slug];
  if (!fr) return null;
  return {
    ...en,
    ...fr,
    sections: fr.sections ?? en.sections,
    extraLinks: fr.extraLinks ?? en.extraLinks,
  };
}

export async function listLocalizedCapabilitySlugs(locale: Locale): Promise<string[]> {
  const { CAPABILITY_PAGES } = await import("./content/capabilities");
  if (locale === "en") return CAPABILITY_PAGES.map((p) => p.slug);
  const fr = await loadFrProgrammatic();
  return CAPABILITY_PAGES.map((p) => p.slug).filter((slug) => Boolean(fr.capabilities?.[slug]));
}
