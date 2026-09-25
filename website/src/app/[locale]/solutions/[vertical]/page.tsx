import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import SolutionVerticalPageView from "@/components/marketing/solutions/SolutionVerticalPageView";
import { routing } from "@/i18n/routing";
import {
  SOLUTION_VERTICAL_SLUGS,
  isValidSolutionVertical,
  solutionVerticalPathSegment,
} from "@/lib/solutions-verticals";
import { SOLUTION_MESSAGE_KEYS } from "@/lib/solutions-hub-config";
import { buildPageMetadata } from "@/lib/seo/page-helpers";

type Props = { params: Promise<{ locale: string; vertical: string }> };

export function generateStaticParams() {
  const params: { locale: string; vertical: string }[] = [];
  for (const locale of routing.locales) {
    for (const vertical of SOLUTION_VERTICAL_SLUGS) {
      params.push({ locale, vertical });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, vertical } = await params;
  if (!isValidSolutionVertical(vertical)) return {};
  if (vertical === "construction") {
    return { alternates: { canonical: `/${locale}/construction` } };
  }
  const messageKey = SOLUTION_MESSAGE_KEYS[vertical];
  const t = await getTranslations({ locale, namespace: `corporate.solutions.${messageKey}` });
  return buildPageMetadata(
    locale,
    solutionVerticalPathSegment(vertical),
    t("meta.title"),
    t("meta.description")
  );
}

export default async function SolutionVerticalPage({ params }: Props) {
  const { locale, vertical } = await params;
  setRequestLocale(locale);
  if (!isValidSolutionVertical(vertical)) notFound();
  if (vertical === "construction") {
    redirect({ href: "/construction", locale });
  }

  return (
    <CorporateShell>
      <SolutionVerticalPageView vertical={vertical} />
    </CorporateShell>
  );
}
