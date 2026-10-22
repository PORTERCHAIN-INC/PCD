"use client";

import { useState } from "react";
import { deliveryOptionLines, type DeliveryOptions } from "@porterchain/types/delivery-options";
import { DeliveryOptionsFields } from "@porterchain/ui/delivery-options-fields";
import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { updateOrderDeliveryOptions } from "@/lib/api";

type Props = {
  orderId: string;
  value: DeliveryOptions | null | undefined;
  /** False once the driver is out for delivery / order closed. */
  editable: boolean;
  onSaved?: (next: DeliveryOptions) => void;
};

/** Per-order delivery options: summary + inline editor (Order360, Shopify orders). */
export default function OrderDeliveryOptionsEditor({ orderId, value, editable, onSaved }: Props) {
  const { getApiToken, orgId } = useMerchantAuth();
  const [current, setCurrent] = useState<DeliveryOptions>(value ?? {});
  const [draft, setDraft] = useState<DeliveryOptions>(value ?? {});
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lines = deliveryOptionLines(current);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const token = await getApiToken();
      if (!token) throw new Error("Sign in again to save");
      const res = await updateOrderDeliveryOptions(token, orderId, draft, orgId ?? undefined);
      setCurrent(res.delivery_options ?? {});
      setOpen(false);
      onSaved?.(res.delivery_options ?? {});
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not save";
      setError(
        msg === "order_not_editable" ? "Too late to change — the order is on its way." : msg
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div data-testid={`order-delivery-options-${orderId}`} className="space-y-2">
      <p className="text-sm text-primary">
        {lines.length ? lines.join(" · ") : <span className="text-muted">No delivery options</span>}
      </p>
      {editable && !open && (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => {
            setDraft(current);
            setOpen(true);
          }}
        >
          Edit delivery options
        </Button>
      )}
      {open && (
        <div className="space-y-2 rounded-xl bg-gray-bg p-3">
          <DeliveryOptionsFields idPrefix={`order-${orderId}`} value={draft} onChange={setDraft} />
          <div className="flex gap-2">
            <Button type="button" size="sm" onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
