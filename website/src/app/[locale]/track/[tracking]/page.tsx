import { Suspense } from "react";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";
import SiteShell from "@/components/layout/SiteShell";
import {
  getOrderByTracking,
  getOrderLiveTracking,
  type OrderLiveTracking,
  type OrderResult,
} from "@/lib/api";
import { ensureStaticParams } from "@/lib/seo/ensure-static-params";
import { routing } from "@/i18n/routing";
import TrackView from "./track-view";

type Props = {
  params: Promise<{ locale: string; tracking: string }>;
};

export function generateStaticParams() {
  return ensureStaticParams(
    routing.locales.map((locale) => ({ locale, tracking: "__build__" })),
    { locale: routing.locales[0]!, tracking: "__build__" }
  );
}

async function TrackData({ locale, tracking }: { locale: string; tracking: string }) {
  const t = await getTranslations({ locale, namespace: "booking.track" });
  let order: OrderResult | null = null;
  let live: OrderLiveTracking | null = null;
  let error: string | null = null;
  try {
    order = await getOrderByTracking(tracking);
  } catch {
    error = t("notFound");
  }
  if (!error) {
    try {
      live = await getOrderLiveTracking(tracking);
    } catch {
      live = null;
    }
  }
  return (
    <TrackView tracking={tracking} initialOrder={order} initialLive={live} initialError={error} />
  );
}

async function TrackFromParams({
  params,
}: {
  params: Promise<{ locale: string; tracking: string }>;
}) {
  const { locale, tracking } = await params;
  setRequestLocale(locale);
  return <TrackData locale={locale} tracking={tracking} />;
}

export default function TrackPage({ params }: Props) {
  return (
    <SiteShell>
      <Suspense
        fallback={
          <RouteLoading label="Loading tracking">
            <PageSkeleton rows={4} />
          </RouteLoading>
        }
      >
        <TrackFromParams params={params} />
      </Suspense>
    </SiteShell>
  );
}
