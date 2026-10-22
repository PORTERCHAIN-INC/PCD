"use client";

import { useEffect, useState } from "react";
import type { DeliveryOptions } from "@porterchain/types/delivery-options";
import { DeliveryOptionsFields } from "@porterchain/ui/delivery-options-fields";
import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { getDeliveryDefaults, saveDeliveryDefaults } from "@/lib/api";

/** Settings → default delivery options. Fills bookings, CSV rows and Shopify orders that chose none. */
export default function DeliveryDefaultsCard() {
  const { getApiToken, orgId } = useMerchantAuth();
  const [value, setValue] = useState<DeliveryOptions>({});
  const [status, setStatus] = useState<"loading" | "idle" | "saving" | "saved" | "error">(
    "loading"
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const token = await getApiToken();
        if (!token) return;
        const next = await getDeliveryDefaults(token, orgId ?? undefined);
        if (live) {
          setValue(next);
          setStatus("idle");
        }
      } catch (err) {
        if (live) {
          setError(err instanceof Error ? err.message : "Could not load defaults");
          setStatus("error");
        }
      }
    })();
    return () => {
      live = false;
    };
  }, [getApiToken, orgId]);

  async function save() {
    setStatus("saving");
    setError(null);
    try {
      const token = await getApiToken();
      if (!token) throw new Error("Sign in again to save");
      setValue(await saveDeliveryDefaults(token, value, orgId ?? undefined));
      setStatus("saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save defaults");
      setStatus("error");
    }
  }

  return (
    <section
      className="space-y-3 rounded-2xl border border-primary/10 bg-white p-6"
      data-testid="delivery-defaults"
    >
      <div>
        <h2 className="text-base font-semibold text-primary">Default delivery options</h2>
        <p className="text-sm text-muted">
          Used for every booking, CSV row and Shopify order that doesn&apos;t set its own (for
          example, always leave at door). You can still change any single order.
        </p>
      </div>
      <DeliveryOptionsFields idPrefix="defaults" value={value} onChange={setValue} />
      <div className="flex items-center gap-3">
        <Button
          type="button"
          size="sm"
          onClick={save}
          disabled={status === "saving" || status === "loading"}
        >
          {status === "saving" ? "Saving…" : "Save defaults"}
        </Button>
        {status === "saved" && <span className="text-sm text-success">Saved</span>}
        {error && (
          <span role="alert" className="text-sm text-danger">
            {error}
          </span>
        )}
      </div>
    </section>
  );
}
