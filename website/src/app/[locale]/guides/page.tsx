import { redirect } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import { localeStaticParams } from "@/lib/seo/page-helpers";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

/** Guides hub merged into /faq — keep individual /guides/[slug] pages. */
export default async function GuidesHubRedirect({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  redirect(`/${locale as Locale}/faq`);
}
