import { Suspense } from "react";
import type { TrackingExperience } from "@porterchain/types";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";
import SiteShell from "@/components/layout/SiteShell";
import {
  getOrderByTracking,
  getOrderExperience,
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
  let experience: TrackingExperience | null = null;
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
    try {
      experience = await getOrderExperience(tracking);
    } catch {
      experience = null;
    }
  }
  return (
    <TrackView
      tracking={tracking}
      initialOrder={order}
      initialLive={live}
      initialExperience={experience}
      initialError={error}
    />
  );
}

/**
 * The tracking number is only known per request, so the whole page (shell included) streams
 * behind one boundary. The server-rendered footer needs the locale, which is set here first.
 */
async function TrackFromParams({
  params,
}: {
  params: Promise<{ locale: string; tracking: string }>;
}) {
  const { locale, tracking } = await params;
  setRequestLocale(locale);
  return (
    <SiteShell>
      <Suspense fallback={<TrackFallback />}>
        <TrackData locale={locale} tracking={tracking} />
      </Suspense>
    </SiteShell>
  );
}

function TrackFallback() {
  return (
    <RouteLoading label="Loading tracking">
      <PageSkeleton rows={4} />
    </RouteLoading>
  );
}

export default function TrackPage({ params }: Props) {
  return (
    <Suspense fallback={<TrackFallback />}>
      <TrackFromParams params={params} />
    </Suspense>
  );
}
