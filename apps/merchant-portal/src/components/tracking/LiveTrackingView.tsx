"use client";

import MerchantLogo from "@/components/branding/MerchantLogo";
import { OrderStateBadge } from "@/components/orders/OrderStateBadge";
import { CopyPublicTrackLink } from "@/components/tracking/CopyPublicTrackLink";
import { DeliveryTimeline } from "@/components/tracking/DeliveryTimeline";
import { PodGallery } from "@/components/tracking/PodGallery";
import { TrackingMap } from "@/components/tracking/TrackingMap";
import { orderStateLabel, vehicleLabel } from "@/lib/catalog";
import { formatEta, type LiveTracking } from "@/lib/tracking";
import { etaSourceLabel } from "@porterchain/maps";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import { useEffect, useState } from "react";

type Props = {
  tracking: LiveTracking;
  onRefresh?: () => void;
  refreshing?: boolean;
  /** When true, link to the order. Off on Order 360 (already there). */
  showOrderLink?: boolean;
  /** Supplied on signed-in pages so POD can be downloaded (BR). */
  getApiToken?: () => Promise<string>;
  orgId?: string;
};

export function LiveTrackingView({
  tracking,
  onRefresh,
  refreshing,
  showOrderLink = true,
  getApiToken,
  orgId,
}: Props) {
  const [showTraffic, setShowTraffic] = useState(false);
  const [replayIndex, setReplayIndex] = useState<number | null>(null);
  const [replayPlaying, setReplayPlaying] = useState(false);

  const replay = tracking.replay ?? [];
  const timeline = tracking.timeline ?? tracking.tracking_history ?? [];

  useEffect(() => {
    if (!replayPlaying || replay.length < 2) return;
    let idx = 0;
    setReplayIndex(0);
    const timer = setInterval(() => {
      idx += 1;
      if (idx >= replay.length) {
        setReplayPlaying(false);
        clearInterval(timer);
        return;
      }
      setReplayIndex(idx);
    }, 800);
    return () => clearInterval(timer);
  }, [replayPlaying, replay.length]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <MerchantLogo
            src={tracking.branding?.logo_url}
            name={tracking.branding?.company_name}
            size="md"
          />
          <div>
            <p className="font-mono text-lg font-bold">{tracking.tracking_number}</p>
            {tracking.order_number && (
              <p className="text-xs text-muted">Order {tracking.order_number}</p>
            )}
            <p className="mt-1 flex flex-wrap items-center gap-2 text-sm">
              <OrderStateBadge state={tracking.state} displayState={tracking.display_state} />
              {tracking.scheduled_at && (
                <span className="text-muted">Scheduled {formatDate(tracking.scheduled_at)}</span>
              )}
              {refreshing && <span className="text-secondary">Updating…</span>}
            </p>
            {tracking.branding?.tracking_page_message ? (
              <p className="mt-1 text-sm text-muted">{tracking.branding.tracking_page_message}</p>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {showOrderLink && tracking.order_id && (
            <Link
              href={`/orders/${tracking.order_id}?tab=tracking`}
              className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs hover:bg-gray-bg"
            >
              Open order
            </Link>
          )}
          <CopyPublicTrackLink
            trackingNumber={tracking.tracking_number}
            publicUrl={tracking.public_track_url}
            isSandbox={Boolean(tracking.is_sandbox)}
          />
          <label className="flex items-center gap-2 rounded-xl border border-primary/15 px-3 py-1.5 text-xs">
            <input
              type="checkbox"
              checked={showTraffic}
              onChange={(e) => setShowTraffic(e.target.checked)}
            />
            Traffic layer
          </label>
          {replay.length > 1 && (
            <button
              type="button"
              className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs hover:bg-gray-bg"
              onClick={() => setReplayPlaying((p) => !p)}
            >
              {replayPlaying ? "Stop replay" : "Delivery replay"}
            </button>
          )}
          {onRefresh && (
            <button
              type="button"
              className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs hover:bg-gray-bg"
              onClick={onRefresh}
            >
              Refresh
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          <TrackingMap
            tracking={tracking}
            showTraffic={showTraffic}
            replayIndex={replayIndex ?? undefined}
          />
          <div className="flex flex-wrap gap-4 text-xs text-muted">
            <span className="flex items-center gap-1">
              <span className="inline-block h-0.5 w-4 bg-violet-600" /> Planned corridor (Valhalla)
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-0.5 w-4 bg-sky-500" /> Remaining path (OSRM)
            </span>
          </div>
        </div>

        <aside className="space-y-4">
          <StatusCard tracking={tracking} />
          <DriverVehicleCard tracking={tracking} />
          {tracking.notifications && tracking.notifications.length > 0 && (
            <section className="rounded-2xl border border-primary/10 bg-white p-4">
              <h3 className="font-semibold text-primary">Notifications</h3>
              <ul className="mt-2 space-y-2 text-sm">
                {tracking.notifications.map((n) => (
                  <li key={String(n.id)} className="rounded-lg bg-gray-bg px-2 py-1.5">
                    <p className="font-medium">{String(n.title)}</p>
                    <p className="text-xs text-muted">{String(n.body)}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-primary/10 bg-white p-5">
          <h3 className="font-semibold text-primary">Delivery timeline</h3>
          <div className="mt-4">
            <DeliveryTimeline events={timeline} />
          </div>
        </section>
        <section className="rounded-2xl border border-primary/10 bg-white p-5">
          <h3 className="font-semibold text-primary">Proof of delivery</h3>
          <div className="mt-4">
            <PodGallery
              pod={tracking.proof_of_delivery ?? {}}
              orderId={tracking.order_id}
              getToken={getApiToken}
              orgId={orgId}
            />
          </div>
        </section>
      </div>
    </div>
  );
}

function StatusCard({ tracking }: { tracking: LiveTracking }) {
  const eta = tracking.eta;
  const sourceCaption = etaSourceLabel(eta?.source);
  const isApprox = eta?.source === "haversine";
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-4">
      <h3 className="font-semibold text-primary">Delivery status</h3>
      <p className="mt-2 text-sm font-medium">
        {orderStateLabel(
          String(tracking.delivery_status?.label ?? tracking.display_state ?? tracking.state)
        )}
      </p>
      {eta && (
        <div className="mt-3 rounded-xl bg-sky-50 p-3">
          <p className="text-xs font-medium text-sky-900">ETA</p>
          <p className="text-xl font-bold text-sky-950">
            {isApprox ? "No road ETA" : (eta.label ?? formatEta(eta.duration_seconds))}
          </p>
          {sourceCaption && <p className="mt-0.5 text-xs text-sky-800">{sourceCaption}</p>}
          {eta.arrives_at && !isApprox && (
            <p className="text-xs text-sky-800">Arrives ~{formatDate(eta.arrives_at)}</p>
          )}
          {typeof eta.distance_meters === "number" && (
            <p className="mt-1 text-xs text-sky-700">
              {(eta.distance_meters / 1000).toFixed(1)} {isApprox ? "km approx" : "km remaining"}
            </p>
          )}
        </div>
      )}
      <p className="mt-2 text-xs text-muted">
        Last update: {tracking.last_updated ? formatDate(tracking.last_updated) : "—"} · GPS from
        Driver GPS
      </p>
    </section>
  );
}

function DriverVehicleCard({ tracking }: { tracking: LiveTracking }) {
  const driver = tracking.driver;
  const vehicle = tracking.vehicle;
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-4">
      <h3 className="font-semibold text-primary">Driver & vehicle</h3>
      {driver ? (
        <div className="mt-2 text-sm">
          <p className="font-medium">{String(driver.name ?? "—")}</p>
          <p className="text-muted">{String(driver.phone ?? "")}</p>
          {driver.is_online != null && (
            <p className="text-xs text-muted">{driver.is_online ? "Online" : "Offline"}</p>
          )}
        </div>
      ) : (
        <p className="mt-2 text-sm text-muted">No driver assigned</p>
      )}
      {vehicle ? (
        <div className="mt-3 border-t border-primary/10 pt-3 text-sm">
          <p className="font-medium">{String(vehicle.label ?? "—")}</p>
          <p className="text-muted">{vehicleLabel(String(vehicle.vehicle_class ?? ""))}</p>
          <p className="text-muted">Plate: {String(vehicle.plate_number ?? "—")}</p>
        </div>
      ) : (
        <p className="mt-2 text-sm text-muted">No vehicle data</p>
      )}
    </section>
  );
}
