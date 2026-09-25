"use client";

import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { drivers, type DriverDetail } from "@/lib/drivers";
import { Button, SectionCard } from "@/components/crm/primitives";
import { Detail } from "@/components/drivers/DriverDetailShared";

export function IdentityTab({
  d,
  canWrite,
  onChanged,
}: {
  d: DriverDetail;
  canWrite: boolean;
  onChanged: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const raw = d.documents as Record<string, unknown>;
  const addr = (raw.address as Record<string, string>) ?? {};
  const emergency = (raw.emergency_contact as Record<string, string>) ?? {};
  const [editing, setEditing] = useState(false);
  const [fullName, setFullName] = useState(d.full_name);
  const [phone, setPhone] = useState(d.phone || "");
  const [licenseClass, setLicenseClass] = useState(d.license_class || "");
  const [serviceArea, setServiceArea] = useState(d.service_area || "");
  const [street, setStreet] = useState(addr.street || "");
  const [city, setCity] = useState(addr.city || "");
  const [province, setProvince] = useState(addr.province || "");
  const [postal, setPostal] = useState(addr.postal_code || "");
  const [emergencyName, setEmergencyName] = useState(emergency.name || "");
  const [emergencyPhone, setEmergencyPhone] = useState(emergency.phone || "");
  const [error, setError] = useState<string | null>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const token = await getApiToken();
      await drivers.updateProfile(token, d.id, {
        full_name: fullName,
        phone,
        license_class: licenseClass,
        service_area: serviceArea,
        address: { street, city, province, postal_code: postal },
        emergency_contact: { name: emergencyName, phone: emergencyPhone },
      });
      setEditing(false);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save identity");
    }
  }

  return (
    <SectionCard
      title="Identity & personal information"
      action={
        canWrite ? (
          <Button variant="outline" onClick={() => setEditing((v) => !v)}>
            {editing ? "Close" : "Edit"}
          </Button>
        ) : undefined
      }
    >
      {editing ? (
        <form onSubmit={save} className="grid gap-3 p-5 sm:grid-cols-2">
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Full name"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Phone"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={licenseClass}
            onChange={(e) => setLicenseClass(e.target.value)}
            placeholder="License class"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={serviceArea}
            onChange={(e) => setServiceArea(e.target.value)}
            placeholder="Service area"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm sm:col-span-2"
            value={street}
            onChange={(e) => setStreet(e.target.value)}
            placeholder="Street"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="City"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={province}
            onChange={(e) => setProvince(e.target.value)}
            placeholder="Province"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={postal}
            onChange={(e) => setPostal(e.target.value)}
            placeholder="Postal code"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={emergencyName}
            onChange={(e) => setEmergencyName(e.target.value)}
            placeholder="Emergency contact"
          />
          <input
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={emergencyPhone}
            onChange={(e) => setEmergencyPhone(e.target.value)}
            placeholder="Emergency phone"
          />
          {error && <p className="text-sm text-red-600 sm:col-span-2">{error}</p>}
          <Button type="submit">Save identity</Button>
        </form>
      ) : (
        <dl className="grid grid-cols-2 gap-4 p-5 md:grid-cols-3">
          <Detail label="Full name" value={d.full_name} />
          <Detail label="Email" value={d.email} />
          <Detail label="Phone" value={d.phone} />
          <Detail
            label="Address"
            value={
              [addr.street, addr.city, addr.province, addr.postal_code]
                .filter(Boolean)
                .join(", ") || null
            }
          />
          <Detail label="Employment type" value={raw.employment_type as string} />
          <Detail
            label="Languages"
            value={
              Array.isArray(raw.languages)
                ? (raw.languages as string[]).join(", ")
                : (raw.languages as string)
            }
          />
          <Detail label="Emergency contact" value={emergency.name} />
          <Detail label="Emergency phone" value={emergency.phone} />
          <Detail
            label="Tax / SIN on file"
            value={raw.sin ? "Provided" : raw.tax_id ? "Provided" : null}
          />
          <Detail label="Fleetbase driver id" value={d.fleetbase_driver_id} />
        </dl>
      )}
    </SectionCard>
  );
}
