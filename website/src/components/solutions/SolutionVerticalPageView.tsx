import { getTranslations } from "next-intl/server";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import SolutionsTabNav from "@/components/solutions/SolutionsTabNav";
import MarketingHero from "@/components/marketing/MarketingHero";
import SolutionVerticalHub from "@/components/solutions/SolutionVerticalHub";
import { solutionVerticalPath, type SolutionVerticalSlug } from "@/lib/solutions-verticals";
import { SOLUTION_MESSAGE_KEYS } from "@/lib/solutions-hub-config";

const SECONDARY_INDUSTRY: Partial<Record<SolutionVerticalSlug, string>> = {
  construction: "construction-materials",
  "3pl": "ecommerce",
  "fleet-overflow": "construction-materials",
};

function secondaryHrefForVertical(vertical: SolutionVerticalSlug): string {
  const industryPath = SECONDARY_INDUSTRY[vertical];
  if (industryPath) return `/industry/${industryPath}`;
  return "/business#industries";
}

/** Shared body for `/solutions/[vertical]` and the short `/construction` alias. */
export default async function SolutionVerticalPageView({
  vertical,
}: {
  vertical: SolutionVerticalSlug;
}) {
  const messageKey = SOLUTION_MESSAGE_KEYS[vertical];
  const t = await getTranslations(`corporate.solutions.${messageKey}`);
  const tBc = await getTranslations("corporate.breadcrumbs");
  const path = solutionVerticalPath(vertical);
  const secondaryHref = secondaryHrefForVertical(vertical);

  return (
    <>
      <PageBreadcrumbs
        items={[
          { label: tBc("home"), href: "/" },
          { label: tBc("solutions"), href: "/solutions" },
          { label: t("breadcrumb") },
        ]}
      />
      <SolutionsTabNav />
      <MarketingHero
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref={`/sign-up?intent=quote&from=${path.replace(/^\//, "")}`}
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref={secondaryHref}
        variant="light-centered"
        trackSource={path.replace(/^\//, "")}
      />
      <SolutionVerticalHub vertical={vertical} />
    </>
  );
}
