"use client";

import { useState } from "react";
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { publicEnv } from "@/lib/env";
import { merchants, type MerchantLocations } from "@/lib/merchants";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import { Badge, Button, Field, Input, SectionCard, Select } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";

const emptyPlace = (): BookingAddress => ({ formatted: "" });

type AddressRow = MerchantLocations["addresses"][number];
type RecipientRow = MerchantLocations["recipients"][number];

export default function MerchantLocationsPanel({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data, error } = useApiData((t) => merchants.locations(t, id), [id, version], {
    key: `merchant-locations-${id}`,
  });
  const [editingAddressId, setEditingAddressId] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [addressType, setAddressType] = useState("pickup");
  const [place, setPlace] = useState<BookingAddress>(emptyPlace);
  const [editingRecipientId, setEditingRecipientId] = useState<string | null>(null);
  const [recipient, setRecipient] = useState({ name: "", email: "", phone: "", company: "" });
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const refresh = () => setVersion((v) => v + 1);
  const addresses = data?.addresses ?? [];
  const recipients = data?.recipients ?? [];

  function resetAddressForm() {
    setEditingAddressId(null);
    setLabel("");
    setAddressType("pickup");
    setPlace(emptyPlace());
  }

  function startEditAddress(row: AddressRow) {
    setEditingAddressId(row.id);
    setLabel(row.label);
    setAddressType(row.address_type || "pickup");
    setPlace({
      formatted: row.formatted,
      postal: row.postal ?? undefined,
      lat: row.lat ?? undefined,
      lng: row.lng ?? undefined,
    });
    setFormError(null);
  }

  function resetRecipientForm() {
    setEditingRecipientId(null);
    setRecipient({ name: "", email: "", phone: "", company: "" });
  }

  function startEditRecipient(row: RecipientRow) {
    setEditingRecipientId(row.id);
    setRecipient({
      name: row.name,
      email: row.email ?? "",
      phone: row.phone ?? "",
      company: row.company ?? "",
    });
    setFormError(null);
  }

  async function saveAddress() {
    if (!label.trim() || !place.formatted.trim()) {
      setFormError("Add a label and choose an Ontario address.");
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      const token = await getApiToken();
      const body = {
        label: label.trim(),
        address_type: addressType,
        formatted: place.formatted.trim(),
        postal: place.postal,
        lat: place.lat,
        lng: place.lng,
        place_id: place.placeId,
        is_default: editingAddressId
          ? addresses.find((a) => a.id === editingAddressId)?.is_default
          : addresses.length === 0,
      };
      if (editingAddressId) {
        await merchants.updateAddress(token, id, editingAddressId, {
          label: body.label,
          address_type: body.address_type,
          formatted: body.formatted,
          postal: body.postal,
          lat: body.lat,
          lng: body.lng,
          place_id: body.place_id,
        });
      } else {
        await merchants.createAddress(token, id, body);
      }
      resetAddressForm();
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not save this location");
    } finally {
      setBusy(false);
    }
  }

  async function makeDefault(addressId: string) {
    setBusy(true);
    setFormError(null);
    try {
      const token = await getApiToken();
      await merchants.setDefaultAddress(token, id, addressId);
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not set the default dock");
    } finally {
      setBusy(false);
    }
  }

  async function removeAddress(addressId: string) {
    if (!window.confirm("Remove this location from the company file?")) return;
    setBusy(true);
    setFormError(null);
    try {
      const token = await getApiToken();
      await merchants.deleteAddress(token, id, addressId);
      if (editingAddressId === addressId) resetAddressForm();
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not remove this location");
    } finally {
      setBusy(false);
    }
  }

  async function saveRecipient() {
    if (!recipient.name.trim()) {
      setFormError("Recipient name is required.");
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      const token = await getApiToken();
      const body = {
        name: recipient.name.trim(),
        email: recipient.email.trim() || undefined,
        phone: recipient.phone.trim() || undefined,
        company: recipient.company.trim() || undefined,
      };
      if (editingRecipientId) await merchants.updateRecipient(token, id, editingRecipientId, body);
      else await merchants.createRecipient(token, id, body);
      resetRecipientForm();
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not save this recipient");
    } finally {
      setBusy(false);
    }
  }

  async function removeRecipient(recipientId: string) {
    if (!window.confirm("Remove this recipient?")) return;
    setBusy(true);
    setFormError(null);
    try {
      const token = await getApiToken();
      await merchants.deleteRecipient(token, id, recipientId);
      if (editingRecipientId === recipientId) resetRecipientForm();
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not remove this recipient");
    } finally {
      setBusy(false);
    }
  }

  return (
    <GoogleMapsProvider>
      <div className="space-y-5">
        {formError ? (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {formError}
          </p>
        ) : null}
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <div className="grid gap-5 lg:grid-cols-2">
          <SectionCard title={`Locations (${addresses.length})`}>
            <div className="divide-y divide-primary/5">
              {addresses.map((row) => (
                <div
                  key={row.id}
                  className="flex flex-wrap items-start justify-between gap-2 px-5 py-3"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-primary">
                      {row.label}{" "}
                      {row.is_default ? <Badge tone="blue">Default pickup</Badge> : null}
                    </p>
                    <p className="text-xs text-muted">
                      {titleCase(row.address_type)} · {row.formatted}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" disabled={busy} onClick={() => startEditAddress(row)}>
                      Edit
                    </Button>
                    {!row.is_default ? (
                      <Button
                        variant="outline"
                        disabled={busy}
                        onClick={() => void makeDefault(row.id)}
                      >
                        Set default
                      </Button>
                    ) : null}
                    <Button
                      variant="danger"
                      disabled={busy}
                      onClick={() => void removeAddress(row.id)}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
              {addresses.length === 0 ? (
                <p className="px-5 py-8 text-center text-sm text-muted">
                  No docks yet. Add the default pickup used on booking.
                </p>
              ) : null}
            </div>
            <div className="space-y-3 border-t border-primary/10 p-5">
              <p className="text-sm font-medium text-primary">
                {editingAddressId ? "Edit location" : "Add location"}
              </p>
              <Field label="Label">
                <Input
                  placeholder="Main warehouse"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                />
              </Field>
              <Field label="Type">
                <Select value={addressType} onChange={(e) => setAddressType(e.target.value)}>
                  <option value="pickup">Pickup</option>
                  <option value="warehouse">Warehouse</option>
                </Select>
              </Field>
              <div>
                <p className="mb-1 text-xs font-medium text-muted">Address</p>
                <AddressAutocompleteInput
                  id={`admin-merchant-location-${id}`}
                  value={place.formatted}
                  onChange={(formatted) => setPlace({ ...place, formatted })}
                  onPlaceSelect={setPlace}
                  apiKey={publicEnv.googleMapsApiKey}
                  placeholder="Ontario address"
                  fallbackClassName="w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => void saveAddress()} disabled={busy}>
                  {editingAddressId ? "Save location" : "Add location"}
                </Button>
                {editingAddressId ? (
                  <Button variant="outline" disabled={busy} onClick={resetAddressForm}>
                    Cancel
                  </Button>
                ) : null}
              </div>
            </div>
          </SectionCard>

          <SectionCard title={`Delivery contacts (${recipients.length})`}>
            <div className="divide-y divide-primary/5">
              {recipients.map((row) => (
                <div
                  key={row.id}
                  className="flex flex-wrap items-start justify-between gap-2 px-5 py-3"
                >
                  <div>
                    <p className="text-sm font-medium text-primary">{row.name}</p>
                    <p className="text-xs text-muted">
                      {[row.company, row.email, row.phone].filter(Boolean).join(" · ") || "—"}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      disabled={busy}
                      onClick={() => startEditRecipient(row)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="danger"
                      disabled={busy}
                      onClick={() => void removeRecipient(row.id)}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
              {recipients.length === 0 ? (
                <p className="px-5 py-8 text-center text-sm text-muted">
                  No delivery recipients yet.
                </p>
              ) : null}
            </div>
            <div className="grid gap-3 border-t border-primary/10 p-5 sm:grid-cols-2">
              <p className="text-sm font-medium text-primary sm:col-span-2">
                {editingRecipientId ? "Edit recipient" : "Add recipient"}
              </p>
              <Field label="Name">
                <Input
                  value={recipient.name}
                  onChange={(e) => setRecipient({ ...recipient, name: e.target.value })}
                />
              </Field>
              <Field label="Company">
                <Input
                  value={recipient.company}
                  onChange={(e) => setRecipient({ ...recipient, company: e.target.value })}
                />
              </Field>
              <Field label="Email">
                <Input
                  type="email"
                  value={recipient.email}
                  onChange={(e) => setRecipient({ ...recipient, email: e.target.value })}
                />
              </Field>
              <Field label="Phone">
                <Input
                  value={recipient.phone}
                  onChange={(e) => setRecipient({ ...recipient, phone: e.target.value })}
                />
              </Field>
              <div className="flex flex-wrap gap-2 sm:col-span-2">
                <Button onClick={() => void saveRecipient()} disabled={busy}>
                  {editingRecipientId ? "Save recipient" : "Add recipient"}
                </Button>
                {editingRecipientId ? (
                  <Button variant="outline" disabled={busy} onClick={resetRecipientForm}>
                    Cancel
                  </Button>
                ) : null}
              </div>
            </div>
          </SectionCard>
        </div>
      </div>
    </GoogleMapsProvider>
  );
}
