import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import AppClerkProvider from "@/components/providers/AppClerkProvider";
import { buildPageMetadata } from "@/lib/seo/page-helpers";

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

/**
 * Clerk (~300 KB of JS from the Clerk CDN) loads only on auth routes. Marketing pages render
 * without it — readiness audit #2 (mobile LCP/TBT). The navbar already shows a plain
 * "Log in" link outside these routes (SiteNavbarAuth / isClerkClientShellPath).
 */
/**
 * Account pages: self-canonical + noindex,follow. Without this they inherited the locale
 * root canonical (/en), so every /sign-up?… variant told Google "I am the home page".
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "login" });
  return buildPageMetadata(
    locale,
    "sign-up",
    `${t("signUpTitle")} | Porterchain`,
    t("signUpSubtitle"),
    {
      index: false,
    }
  );
}

export default async function AuthRouteLayout({ children, params }: Props) {
  const { locale } = await params;
  return <AppClerkProvider locale={locale}>{children}</AppClerkProvider>;
}
