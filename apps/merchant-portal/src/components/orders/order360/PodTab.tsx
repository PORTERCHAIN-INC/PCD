"use client";

import { PodGallery } from "@/components/tracking/PodGallery";
import type { OrderDetail } from "@/lib/orders";
import { Card } from "./shared";

export function PodTab({
  pod,
  orderId,
  getApiToken,
  orgId,
}: {
  pod: Record<string, unknown>;
  orderId: string;
  getApiToken?: () => Promise<string>;
  orgId?: string;
}) {
  const empty = !pod || Object.keys(pod).length === 0;
  return (
    <Card title="Proof of delivery">
      {empty ? (
        <p className="text-muted">POD will appear after delivery is completed.</p>
      ) : (
        <PodGallery pod={pod} orderId={orderId} getToken={getApiToken} orgId={orgId} />
      )}
    </Card>
  );
}
