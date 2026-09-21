"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import { TrackEtaPanel, TrackRouteMap } from "@porterchain/maps";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import GuestTrackLookup from "@/components/portal/GuestTrackLookup";
import {
  getOrderByTracking,
  getOrderLiveTracking,
  type OrderLiveTracking,
  type OrderResult,
} from "@/lib/api";

export default function TrackPage() {
  const t = useTranslations("booking.track");
  const portalT = useTranslations("portal.customer");
  const params = useParams();
  const tracking = typeof params.tracking === "string" ? params.tracking : "";
  const [order, setOrder] = useState<OrderResult | null>(null);
  const [live, setLive] = useState<OrderLiveTracking | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!tracking) return;
    getOrderByTracking(tracking)
      .then(setOrder)
      .catch(() => setError(t("notFound")));
    getOrderLiveTracking(tracking)
      .then(setLive)
      .catch(() => setLive(null));
  }, [tracking, t]);

  const liveData = live?.live_tracking;
  const pickup = liveData?.pickup ?? order?.pickup;
  const dropoff = liveData?.dropoff ?? order?.dropoff;
  const driverLocation = liveData?.driver_location ?? null;
  const routePolyline = liveData?.optimized_route?.polyline ?? liveData?.eta?.polyline ?? null;
  const eta = liveData?.eta ?? null;
  const delivered = Boolean(liveData?.delivery_status?.delivered);

  return (
    <SiteShell>
      <Container className="py-16 md:py-24 max-w-lg">
        <h1 className="type-h2 font-bold text-primary mb-2">{t("title")}</h1>
        <p className="type-caption text-muted font-mono mb-8">{tracking}</p>
        {error && (
          <div className="mb-6 space-y-2">
            <p className="text-red-600">{error}</p>
            <p className="type-small text-muted">
              Test or sandbox tracking numbers are not shown on the public track page. Use the
              merchant portal for test bookings.
            </p>
          </div>
        )}
        {order && (
          <>
            {(order.logo_url || order.company_name || order.tracking_page_message) && (
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
            <p className="mb-6 text-xs text-muted">
              Snapshot from the API. Driver GPS is Fleetbase (polled). Road ETA is OSRM when a live
              remaining path exists. Refresh this page to update — this is not a map WebSocket.
            </p>
            <dl className="space-y-3 rounded-2xl bg-gray-bg p-6 mb-8">
              <div className="flex justify-between">
                <dt className="text-muted type-small">{t("status")}</dt>
                <dd className="font-semibold type-small">{order.state}</dd>
              </div>
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

        <div className="rounded-2xl border border-primary/10 bg-white p-5 mb-6">
          <p className="type-small text-primary mb-3">{portalT("trackPortalPrompt")}</p>
          <Link
            href="/login"
            className="inline-flex rounded-xl bg-secondary px-4 py-2.5 text-white font-semibold type-small hover:bg-[#1d4ed8]"
          >
            {portalT("trackPortalCta")}
          </Link>
        </div>

        <GuestTrackLookup />
      </Container>
    </SiteShell>
  );
}
