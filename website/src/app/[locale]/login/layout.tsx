import AppClerkProvider from "@/components/providers/AppClerkProvider";

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

/**
 * Clerk (~300 KB of JS from the Clerk CDN) loads only on auth routes. Marketing pages render
 * without it — readiness audit #2 (mobile LCP/TBT). The navbar already shows a plain
 * "Log in" link outside these routes (SiteNavbarAuth / isClerkClientShellPath).
 */
export default async function AuthRouteLayout({ children, params }: Props) {
  const { locale } = await params;
  return <AppClerkProvider locale={locale}>{children}</AppClerkProvider>;
}
