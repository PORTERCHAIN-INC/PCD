"use client";

import Link from "next/link";
import { useState } from "react";
import Button from "@/components/ui/Button";
import { claimStatusLabel, claimTypeLabel } from "@/lib/catalog";
import { ordersApi, type OrderDetail } from "@/lib/orders";
import { settingsApi } from "@/lib/settings";
import { formatCents, formatDate } from "@/lib/utils";
import { Card } from "./shared";

export function ClaimsTab({
  claims,
  orderId,
  getApiToken,
  orgId,
  onRefresh,
}: {
  claims: Array<Record<string, unknown>>;
  orderId: string;
  getApiToken?: () => Promise<string>;
  orgId?: string;
  onRefresh: () => void;
}) {
  const [claimType, setClaimType] = useState("merchant_complaint");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!getApiToken) return;
    setSubmitting(true);
    setError(null);
    try {
      const token = await getApiToken();
      await settingsApi.openClaim(
        token,
        { order_id: orderId, claim_type: claimType, description },
        orgId
      );
      setDescription("");
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That order was not found.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card title="Claims">
      {getApiToken && (
        <div className="mb-4 space-y-2 border-b border-primary/10 pb-4">
          <select
            className="w-full rounded-lg border px-3 py-2 text-sm"
            value={claimType}
            onChange={(e) => setClaimType(e.target.value)}
          >
            <option value="merchant_complaint">{claimTypeLabel("merchant_complaint")}</option>
            <option value="damaged_parcel">{claimTypeLabel("damaged_parcel")}</option>
            <option value="lost_parcel">{claimTypeLabel("lost_parcel")}</option>
            <option value="late_delivery">{claimTypeLabel("late_delivery")}</option>
          </select>
          <textarea
            className="w-full rounded-lg border px-3 py-2 text-sm"
            rows={2}
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button size="sm" onClick={() => void submit()} disabled={submitting}>
            File claim
          </Button>
        </div>
      )}
      {claims.length === 0 ? (
        <p className="text-muted">No claims filed for this order.</p>
      ) : (
        <ul className="space-y-2">
          {claims.map((c) => (
            <li key={String(c.id)} className="rounded-lg border border-primary/10 p-3">
              <p className="font-medium">{claimTypeLabel(String(c.claim_type))}</p>
              <p className="text-muted">
                {claimStatusLabel(String(c.status))}
                {c.created_at ? ` · ${formatDate(String(c.created_at))}` : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
