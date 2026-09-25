"use client";

import { useState } from "react";
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import Button from "@/components/ui/Button";
import { publicEnv } from "@/lib/env";
import { settingsApi, type SettingsOverview } from "@/lib/settings";
import { Field } from "./Field";

export function LocationsTab({
  data,
  onRefresh,
  getToken,
  orgId,
}: {
  data: SettingsOverview;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [pickupLabel, setPickupLabel] = useState("");
  const [pickup, setPickup] = useState<BookingAddress>({ formatted: "" });

  const addPickup = async () => {
    if (!pickupLabel.trim() || !pickup.formatted.trim()) return;
    const token = await getToken();
    await settingsApi.addPickup(
      token,
      {
        label: pickupLabel,
        formatted: pickup.formatted,
        postal: pickup.postal,
        lat: pickup.lat,
        lng: pickup.lng,
        place_id: pickup.placeId,
        is_default: data.pickup_locations.length === 0,
      },
      orgId
    );
    setPickupLabel("");
    setPickup({ formatted: "" });
    await onRefresh();
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Pickup locations</h2>
      <p className="mt-1 text-sm text-muted">
        The default location is pre-filled when you book. Addresses are the company record — not a
        separate warehouse list.
      </p>
      <ul className="mt-4 space-y-2 text-sm">
        {data.pickup_locations.map((p) => (
          <li key={p.id} className="flex justify-between gap-2">
            <span>
              <span className="font-medium">{p.label}</span>
              {p.is_default && (
                <span className="ml-2 rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-secondary">
                  Default
                </span>
              )}
              <span className="block text-muted">{p.formatted}</span>
            </span>
            <span className="flex shrink-0 items-center gap-2">
              {!p.is_default && (
                <button
                  type="button"
                  className="text-xs text-secondary"
                  onClick={() =>
                    void getToken().then((t) =>
                      settingsApi.setDefaultPickup(t, p.id, orgId).then(onRefresh)
                    )
                  }
                >
                  Set default
                </button>
              )}
              <button
                type="button"
                className="text-xs text-red-600"
                onClick={() =>
                  void getToken().then((t) =>
                    settingsApi.deletePickup(t, p.id, orgId).then(onRefresh)
                  )
                }
              >
                Remove
              </button>
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-4 space-y-2">
        <input
          className="w-full rounded-lg border px-3 py-2 text-sm"
          placeholder="Label (e.g. Main warehouse)"
          value={pickupLabel}
          onChange={(e) => setPickupLabel(e.target.value)}
        />
        <AddressAutocompleteInput
          id="settings-pickup"
          value={pickup.formatted}
          onChange={(formatted) => setPickup({ ...pickup, formatted })}
          onPlaceSelect={setPickup}
          apiKey={publicEnv.googleMapsApiKey}
          placeholder="Ontario address"
          fallbackClassName="w-full rounded-lg border px-3 py-2 text-sm"
        />
        <Button size="sm" onClick={() => void addPickup()}>
          Add location
        </Button>
      </div>
    </section>
  );
}
