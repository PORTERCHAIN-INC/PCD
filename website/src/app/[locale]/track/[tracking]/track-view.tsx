"use client";

import { useEffect, useEffectEvent, useState } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { isEnhancedExperience, type TrackingExperience } from "@porterchain/types";
import { Link } from "@/i18n/navigation";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import { TrackEtaPanel, TrackRouteMap } from "@porterchain/maps";
import Container from "@/components/ui/Container";
import TrackLookupForm from "@/components/track/TrackLookupForm";
import TrackStatusSteps from "@/components/track/TrackStatusSteps";
import TrackExperiencePanel from "./TrackExperiencePanel";
import TrackActions from "./TrackActions";
import {
  getOrderByTracking,
  getOrderExperience,
  getOrderLiveTracking,
  type OrderLiveTracking,
  type OrderResult,
} from "@/lib/api";

const POLL_MS = 10_000;

export default function TrackView({
  tracking,
  initialOrder,
  initialLive,
  initialExperience = null,
  initialError,
}: {
  tracking: string;
  initialOrder: OrderResult | null;
  initialLive: OrderLiveTracking | null;
  initialExperience?: TrackingExperience | null;
  initialError: string | null;
}) {
  const t = useTranslations("booking.track");
  const portalT = useTranslations("portal.customer");
  const [order, setOrder] = useState<OrderResult | null>(initialOrder);
  const [live, setLive] = useState<OrderLiveTracking | null>(initialLive);
  const [error, setError] = useState<string | null>(initialError);
  const [experience, setExperience] = useState<TrackingExperience | null>(initialExperience);
  // Signed link from a recipient message (?t=) unlocks POD photos + the manage page.
  const manageToken = useSearchParams().get("t");
  const enhanced = isEnhancedExperience(experience) ? experience : null;
  const manageHref = manageToken
    ? `/track/${encodeURIComponent(tracking)}/manage?t=${encodeURIComponent(manageToken)}`
    : null;
  const delivered = Boolean(live?.live_tracking?.delivery_status?.delivered);

  const onPoll = useEffectEvent(() => {
    getOrderByTracking(tracking)
      .then(setOrder)
      .catch(() => setError(t("notFound")));
    getOrderLiveTracking(tracking)
      .then(setLive)
      .catch(() => setLive(null));
    getOrderExperience(tracking, manageToken)
      .then(setExperience)
      .catch(() => undefined);
  });

  useEffect(() => {
    if (manageToken) onPoll();
  }, [manageToken]);

  useEffect(() => {
    if (!tracking || delivered || error) return;
    const timer = window.setInterval(() => onPoll(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [tracking, delivered, error]);

  const liveData = live?.live_tracking;
  const pickup = liveData?.pickup ?? order?.pickup;
  const dropoff = liveData?.dropoff ?? order?.dropoff;
  const driverLocation = liveData?.driver_location ?? null;
  const routePolyline = liveData?.optimized_route?.polyline ?? liveData?.eta?.polyline ?? null;
  const eta = liveData?.eta ?? null;

  return (
    <Container className="max-w-2xl py-12 md:py-20">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{t("title")}</p>
      <h1 className="mt-1 font-mono text-2xl font-bold tracking-tight text-primary sm:text-3xl">
        {tracking}
      </h1>
      {error && (
        <div className="mt-8 rounded-2xl border border-primary/10 bg-gray-bg p-5" role="alert">
          <p className="font-semibold text-primary">{error}</p>
          <p className="mt-1 text-sm text-muted">{t("notFoundHelp")}</p>
        </div>
      )}
      {order && (
        <div className="mt-8 rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
          <TrackStatusSteps state={order.state} delivered={delivered} />
        </div>
      )}
      <div className="mt-8" />
      {order && (
        <>
          {enhanced ? <TrackExperiencePanel exp={enhanced} manageHref={manageHref} /> : null}
          {manageToken ? (
            <TrackActions tracking={tracking} token={manageToken} refreshKey={order.state} />
          ) : null}
          {!enhanced && (order.logo_url || order.company_name || order.tracking_page_message) && (
            <div className="mb-8 flex items-start gap-3">
              {order.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={order.logo_url}
                  alt={order.company_name ? `${order.company_name} logo` : "Shipper logo"}
                  referrerPolicy="no-referrer"
                  className="h-12 w-12 rounded-lg object-cover"
                />
              ) : null}
              <div>
                {order.company_name ? (
                  <p className="font-semibold text-primary">{order.company_name}</p>
                ) : null}
                {order.tracking_page_message ? (
                  <p className="type-small text-muted mt-1">{order.tracking_page_message}</p>
                ) : null}
              </div>
            </div>
          )}
          <GoogleMapsProvider>
            <TrackRouteMap
              pickup={pickup as Record<string, unknown> | null | undefined}
              dropoff={dropoff as Record<string, unknown> | null | undefined}
              driverLocation={driverLocation}
              routePolyline={routePolyline}
              height="min(50vw, 320px)"
              className="mb-8"
            />
          </GoogleMapsProvider>
          <TrackEtaPanel
            eta={eta}
            delivered={delivered}
            className="mb-6"
            title={t("etaTitle")}
            arrivalPrefix={t("etaArrival")}
            distanceSuffix={t("etaDistance")}
          />
          <dl className="space-y-3 rounded-2xl bg-gray-bg p-6 mb-8">
            <div className="flex justify-between">
              <dt className="text-muted type-small">{t("pickup")}</dt>
              <dd className="type-small text-right max-w-[60%]">
                {pickup?.formatted || [pickup?.city, pickup?.province].filter(Boolean).join(", ")}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted type-small">{t("dropoff")}</dt>
              <dd className="type-small text-right max-w-[60%]">
                {dropoff?.formatted ||
                  [dropoff?.city, dropoff?.province].filter(Boolean).join(", ")}
              </dd>
            </div>
          </dl>
        </>
      )}

      <div className="mt-4 border-t border-primary/10 pt-8">
        <TrackLookupForm size="md" />
        <p className="mt-4 text-sm text-muted">
          {portalT("trackPortalPrompt")}{" "}
          <Link
            href="/login"
            className="font-semibold text-secondary underline-offset-4 hover:underline"
          >
            {portalT("trackPortalCta")}
          </Link>
        </p>
      </div>
    </Container>
  );
}
