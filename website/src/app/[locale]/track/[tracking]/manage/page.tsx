import { Suspense } from "react";
import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";
import SiteShell from "@/components/layout/SiteShell";
import { ensureStaticParams } from "@/lib/seo/ensure-static-params";
import { routing } from "@/i18n/routing";
import ManageView from "./manage-view";

type Props = {
  params: Promise<{ locale: string; tracking: string }>;
};

// Signed recipient links: never index, never leak the token via Referer.
export const metadata: Metadata = {
  title: "Manage your delivery",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export function generateStaticParams() {
  return ensureStaticParams(
    routing.locales.map((locale) => ({ locale, tracking: "__build__" })),
    { locale: routing.locales[0]!, tracking: "__build__" }
  );
}

async function ManageFromParams({ params }: Props) {
  const { locale, tracking } = await params;
  setRequestLocale(locale);
  return <ManageView tracking={tracking} />;
}

export default function ManageDeliveryPage({ params }: Props) {
  return (
    <SiteShell>
      <Suspense
        fallback={
          <RouteLoading label="Loading delivery options">
            <PageSkeleton rows={4} />
          </RouteLoading>
        }
      >
        <ManageFromParams params={params} />
      </Suspense>
    </SiteShell>
  );
}
