"use client";

import { useState } from "react";
import { Link2, Plus } from "lucide-react";
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { customersApi, type CreateCustomerBookingDraftResult } from "@/lib/customers";
import { RETAIL_VEHICLE_OPTIONS } from "@/lib/merchants";
import { money } from "@/lib/crmFormat";
import { publicEnv } from "@/lib/env";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import { Button, Input, Modal, Select } from "@/components/crm/primitives";
import { DateTimeField } from "@porterchain/ui/date-fields";

type Props = {
  customerId: string;
  customerEmail: string;
  open: boolean;
  onClose: () => void;
  onCreated: (result: CreateCustomerBookingDraftResult) => void;
};

const emptyAddress = (): BookingAddress => ({ formatted: "" });

function toLocalInputValue(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function CustomerAddOrderModal({
  customerId,
  customerEmail,
  open,
  onClose,
  onCreated,
}: Props) {
  const { getApiToken } = useAdminAuth();
  const [pickup, setPickup] = useState<BookingAddress>(emptyAddress);
  const [dropoff, setDropoff] = useState<BookingAddress>(emptyAddress);
  const [vehicleClass, setVehicleClass] = useState<string>(RETAIL_VEHICLE_OPTIONS[0]);
  const [packageType, setPackageType] = useState("small");
  const [scheduledAt, setScheduledAt] = useState(() => toLocalInputValue(new Date()));
  const [instructions, setInstructions] = useState("");
  const [sendLink, setSendLink] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!pickup.formatted.trim() || !dropoff.formatted.trim()) {
      setError("Select pickup and dropoff from Google suggestions");
      return;
    }
    if (
      typeof pickup.lat !== "number" ||
      typeof pickup.lng !== "number" ||
      typeof dropoff.lat !== "number" ||
      typeof dropoff.lng !== "number"
    ) {
      setError("Pick addresses from the Google suggestions list (lat/lng required for pricing)");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      const result = await customersApi.createBookingDraft(token, customerId, {
        pickup: {
          formatted: pickup.formatted.trim(),
          place_id: pickup.placeId ?? null,
          lat: pickup.lat,
          lng: pickup.lng,
        },
        dropoff: {
          formatted: dropoff.formatted.trim(),
          place_id: dropoff.placeId ?? null,
          lat: dropoff.lat,
          lng: dropoff.lng,
        },
        vehicle_class: vehicleClass,
        package_type: packageType,
        special_instructions: instructions.trim() || null,
        scheduled_at: new Date(scheduledAt).toISOString(),
        schedule_mode: "now",
        send_payment_link: sendLink,
      });
      onCreated(result);
      setPickup(emptyAddress());
      setDropoff(emptyAddress());
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "create_failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add order"
      panelClassName="max-w-2xl"
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={() => void submit()} disabled={busy}>
            <Plus className="h-4 w-4" />
            {busy ? "Creating…" : sendLink ? "Create + Stripe link" : "Create draft"}
          </Button>
        </div>
      }
    >
      <GoogleMapsProvider>
        <div className="space-y-4 text-sm">
          <p className="text-muted">
            Retail booking for <span className="font-medium text-primary">{customerEmail}</span>.
            Payment is Stripe only — no cash.
          </p>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Pickup</p>
            <AddressAutocompleteInput
              id="admin-customer-pickup"
              value={pickup.formatted}
              onChange={(v) =>
                setPickup((p) => ({
                  ...p,
                  formatted: v,
                  lat: undefined,
                  lng: undefined,
                  placeId: undefined,
                }))
              }
              onPlaceSelect={setPickup}
              placeholder="Start typing pickup address…"
              apiKey={publicEnv.googleMapsApiKey}
              fallbackClassName="w-full rounded-xl border border-primary/15 bg-white px-3 py-2.5 text-sm text-primary outline-none focus:border-secondary"
            />
            {typeof pickup.lat === "number" && (
              <p className="text-xs text-muted">
                Selected · {pickup.lat.toFixed(5)}, {pickup.lng?.toFixed(5)}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Dropoff</p>
            <AddressAutocompleteInput
              id="admin-customer-dropoff"
              value={dropoff.formatted}
              onChange={(v) =>
                setDropoff((p) => ({
                  ...p,
                  formatted: v,
                  lat: undefined,
                  lng: undefined,
                  placeId: undefined,
                }))
              }
              onPlaceSelect={setDropoff}
              placeholder="Start typing dropoff address…"
              apiKey={publicEnv.googleMapsApiKey}
              fallbackClassName="w-full rounded-xl border border-primary/15 bg-white px-3 py-2.5 text-sm text-primary outline-none focus:border-secondary"
            />
            {typeof dropoff.lat === "number" && (
              <p className="text-xs text-muted">
                Selected · {dropoff.lat.toFixed(5)}, {dropoff.lng?.toFixed(5)}
              </p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-muted">Vehicle</span>
              <Select value={vehicleClass} onChange={(e) => setVehicleClass(e.target.value)}>
                {RETAIL_VEHICLE_OPTIONS.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </Select>
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-muted">Package</span>
              <Select value={packageType} onChange={(e) => setPackageType(e.target.value)}>
                <option value="small">Small</option>
                <option value="medium">Medium</option>
                <option value="large">Large</option>
                <option value="extra_large">Extra large</option>
                <option value="skid">Skid</option>
                <option value="furniture">Furniture</option>
                <option value="whole_vehicle">Whole vehicle</option>
              </Select>
            </label>
          </div>
          <DateTimeField
            label="Scheduled"
            value={scheduledAt}
            onChange={setScheduledAt}
            hourFormat={12}
          />
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-muted">Instructions</span>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              rows={2}
              className="w-full rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm outline-none focus:border-secondary"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-primary">
            <input
              type="checkbox"
              checked={sendLink}
              onChange={(e) => setSendLink(e.target.checked)}
              className="rounded border-primary/30"
            />
            <Link2 className="h-4 w-4 text-muted" />
            Send Stripe payment link after create
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
      </GoogleMapsProvider>
    </Modal>
  );
}

export function CustomerOrderCreatedBanner({
  result,
}: {
  result: CreateCustomerBookingDraftResult;
}) {
  return (
    <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-950">
      <p className="font-medium">
        Draft {result.draft_number || result.draft_id.slice(0, 8)} · {money(result.amount_cents)}
      </p>
      <p className="mt-1 text-xs text-muted">
        Quote {result.quote_id.slice(0, 8)}… · state {result.state}
        {result.checkout_url ? " · Stripe link ready" : ""}
      </p>
      <div className="mt-2 flex flex-wrap gap-3">
        <a
          href={`/booking-drafts/${result.draft_id}`}
          className="font-medium text-secondary hover:underline"
        >
          Open draft →
        </a>
        {result.checkout_url && (
          <a
            href={result.checkout_url}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-secondary hover:underline"
          >
            Open Stripe Checkout →
          </a>
        )}
      </div>
    </div>
  );
}
