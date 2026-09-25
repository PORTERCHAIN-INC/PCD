"use client";

import { DeliveryTimeline } from "@/components/tracking/DeliveryTimeline";
import { LiveTrackingView } from "@/components/tracking/LiveTrackingView";
import type { LiveTracking } from "@/lib/tracking";
import { Card } from "./shared";

export function TrackingTab({
  tracking,
  onRefresh,
  refreshing,
  getApiToken,
  orgId,
}: {
  tracking: LiveTracking | null;
  onRefresh: () => void;
  refreshing?: boolean;
  getApiToken?: () => Promise<string>;
  orgId?: string;
}) {
  if (tracking?.order_id && tracking?.tracking_number) {
    return (
      <LiveTrackingView
        tracking={tracking}
        onRefresh={onRefresh}
        refreshing={refreshing}
        showOrderLink={false}
        getApiToken={getApiToken}
        orgId={orgId}
      />
    );
  }

  const history = tracking?.tracking_history ?? tracking?.timeline ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Live status">
        <p className="text-muted">Live location appears once a driver is on the way.</p>
      </Card>
      <Card title="Tracking history">
        <DeliveryTimeline events={history} />
      </Card>
    </div>
  );
}
