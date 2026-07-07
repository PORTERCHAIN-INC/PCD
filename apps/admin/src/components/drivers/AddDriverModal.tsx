"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { drivers, DRIVER_DOC_TYPES, type DriverCreatePayload } from "@/lib/drivers";
import { VEHICLE_CLASSES } from "@/lib/pricing";
import { Button, Drawer, Field, Input, Select, Textarea } from "@/components/crm/primitives";

type DocDraft = {
  doc_type: string;
  label: string;
  file_url: string;
  reference_number: string;
  expires_at: string;
  notes: string;
};

const emptyDoc = (): DocDraft => ({
  doc_type: "driver_license",
  label: "",
  file_url: "",
  reference_number: "",
  expires_at: "",
  notes: "",
});

export function AddDriverModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (driverId: string) => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [licenseClass, setLicenseClass] = useState("");
  const [licenseNumber, setLicenseNumber] = useState("");
  const [employmentType, setEmploymentType] = useState("contractor");
  const [street, setStreet] = useState("");
  const [city, setCity] = useState("");
  const [province, setProvince] = useState("ON");
  const [postalCode, setPostalCode] = useState("");
  const [emergencyName, setEmergencyName] = useState("");
  const [emergencyPhone, setEmergencyPhone] = useState("");
  const [addVehicle, setAddVehicle] = useState(false);
  const [vehicleClass, setVehicleClass] = useState("cargoVan");
  const [plateNumber, setPlateNumber] = useState("");
  const [makeModel, setMakeModel] = useState("");
  const [autoApprove, setAutoApprove] = useState(false);
  const [docs, setDocs] = useState<DocDraft[]>([]);

  function reset() {
    setFullName("");
    setEmail("");
    setPhone("");
    setLicenseClass("");
    setLicenseNumber("");
    setEmploymentType("contractor");
    setStreet("");
    setCity("");
    setProvince("ON");
    setPostalCode("");
    setEmergencyName("");
    setEmergencyPhone("");
    setAddVehicle(false);
    setVehicleClass("cargoVan");
    setPlateNumber("");
    setMakeModel("");
    setAutoApprove(false);
    setDocs([]);
    setError(null);
  }

  function close() {
    reset();
    onClose();
  }

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload: DriverCreatePayload = {
        full_name: fullName.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
        license_class: licenseClass.trim() || undefined,
        license_number: licenseNumber.trim() || undefined,
        employment_type: employmentType || undefined,
        auto_approve: autoApprove,
        address:
          street || city || province || postalCode
            ? {
                street: street.trim() || undefined,
                city: city.trim() || undefined,
                province: province.trim() || undefined,
                postal_code: postalCode.trim() || undefined,
              }
            : undefined,
        emergency_contact:
          emergencyName || emergencyPhone
            ? {
                name: emergencyName.trim() || undefined,
                phone: emergencyPhone.trim() || undefined,
              }
            : undefined,
        vehicle:
          addVehicle && plateNumber.trim()
            ? {
                vehicle_class: vehicleClass,
                plate_number: plateNumber.trim(),
                make_model: makeModel.trim() || undefined,
              }
            : undefined,
        documents: docs
          .filter((d) => d.doc_type)
          .map((d) => ({
            doc_type: d.doc_type,
            label: d.label.trim() || undefined,
            file_url: d.file_url.trim() || undefined,
            reference_number: d.reference_number.trim() || undefined,
            expires_at: d.expires_at ? new Date(d.expires_at).toISOString() : undefined,
            notes: d.notes.trim() || undefined,
          })),
      };
      const token = await getApiToken();
      const created = await drivers.create(token, payload);
      onCreated(created.id);
      close();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not create driver";
      setError(
        msg.includes("driver_email_exists") ? "A driver with this email already exists." : msg
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Drawer
      open={open}
      onClose={close}
      title="Add driver"
      width="max-w-2xl"
      footer={
        <>
          <Button variant="ghost" onClick={close} disabled={busy}>
            Cancel
          </Button>
          <Button disabled={busy || !fullName.trim() || !email.trim()} onClick={() => submit()}>
            {busy ? "Saving…" : "Create driver"}
          </Button>
        </>
      }
    >
      <form id="add-driver-form" onSubmit={submit} className="space-y-6">
        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-primary">Basic information</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Full name *">
              <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            </Field>
            <Field label="Email *">
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </Field>
            <Field label="Phone">
              <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1…" />
            </Field>
            <Field label="Employment type">
              <Select value={employmentType} onChange={(e) => setEmploymentType(e.target.value)}>
                <option value="contractor">Independent contractor</option>
                <option value="employee">Employee</option>
                <option value="fleet_partner">Fleet partner</option>
              </Select>
            </Field>
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-primary">License</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="License class">
              <Input
                value={licenseClass}
                onChange={(e) => setLicenseClass(e.target.value)}
                placeholder="G, AZ…"
              />
            </Field>
            <Field label="License number">
              <Input value={licenseNumber} onChange={(e) => setLicenseNumber(e.target.value)} />
            </Field>
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-primary">Address</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Street" className="sm:col-span-2">
              <Input value={street} onChange={(e) => setStreet(e.target.value)} />
            </Field>
            <Field label="City">
              <Input value={city} onChange={(e) => setCity(e.target.value)} />
            </Field>
            <Field label="Province">
              <Input value={province} onChange={(e) => setProvince(e.target.value)} maxLength={2} />
            </Field>
            <Field label="Postal code">
              <Input value={postalCode} onChange={(e) => setPostalCode(e.target.value)} />
            </Field>
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-primary">Emergency contact</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Name">
              <Input value={emergencyName} onChange={(e) => setEmergencyName(e.target.value)} />
            </Field>
            <Field label="Phone">
              <Input value={emergencyPhone} onChange={(e) => setEmergencyPhone(e.target.value)} />
            </Field>
          </div>
        </section>

        <section className="space-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-primary">
            <input
              type="checkbox"
              checked={addVehicle}
              onChange={(e) => setAddVehicle(e.target.checked)}
            />
            Register a vehicle
          </label>
          {addVehicle && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Vehicle class">
                <Select value={vehicleClass} onChange={(e) => setVehicleClass(e.target.value)}>
                  {VEHICLE_CLASSES.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Plate number *">
                <Input
                  value={plateNumber}
                  onChange={(e) => setPlateNumber(e.target.value)}
                  required={addVehicle}
                />
              </Field>
              <Field label="Make / model" className="sm:col-span-2">
                <Input
                  value={makeModel}
                  onChange={(e) => setMakeModel(e.target.value)}
                  placeholder="Ford Transit…"
                />
              </Field>
            </div>
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-primary">Documents</h3>
            <Button
              type="button"
              variant="outline"
              onClick={() => setDocs((d) => [...d, emptyDoc()])}
            >
              <Plus className="h-4 w-4" /> Add document
            </Button>
          </div>
          {docs.length === 0 && (
            <p className="text-sm text-muted">
              Optional — add license, insurance, or background check records.
            </p>
          )}
          {docs.map((doc, i) => (
            <div key={i} className="space-y-3 rounded-xl border border-primary/10 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted">Document {i + 1}</span>
                <button
                  type="button"
                  className="rounded-lg p-1 text-muted hover:bg-gray-bg hover:text-red-600"
                  onClick={() => setDocs((d) => d.filter((_, j) => j !== i))}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Type">
                  <Select
                    value={doc.doc_type}
                    onChange={(e) =>
                      setDocs((d) =>
                        d.map((row, j) => (j === i ? { ...row, doc_type: e.target.value } : row))
                      )
                    }
                  >
                    {DRIVER_DOC_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Label">
                  <Input
                    value={doc.label}
                    onChange={(e) =>
                      setDocs((d) =>
                        d.map((row, j) => (j === i ? { ...row, label: e.target.value } : row))
                      )
                    }
                    placeholder="Optional display name"
                  />
                </Field>
                <Field label="File URL" className="sm:col-span-2">
                  <Input
                    value={doc.file_url}
                    onChange={(e) =>
                      setDocs((d) =>
                        d.map((row, j) => (j === i ? { ...row, file_url: e.target.value } : row))
                      )
                    }
                    placeholder="https://… or internal storage path"
                  />
                </Field>
                <Field label="Reference / policy number">
                  <Input
                    value={doc.reference_number}
                    onChange={(e) =>
                      setDocs((d) =>
                        d.map((row, j) =>
                          j === i ? { ...row, reference_number: e.target.value } : row
                        )
                      )
                    }
                  />
                </Field>
                <Field label="Expires">
                  <Input
                    type="date"
                    value={doc.expires_at}
                    onChange={(e) =>
                      setDocs((d) =>
                        d.map((row, j) => (j === i ? { ...row, expires_at: e.target.value } : row))
                      )
                    }
                  />
                </Field>
                <Field label="Notes" className="sm:col-span-2">
                  <Textarea
                    value={doc.notes}
                    onChange={(e) =>
                      setDocs((d) =>
                        d.map((row, j) => (j === i ? { ...row, notes: e.target.value } : row))
                      )
                    }
                    rows={2}
                  />
                </Field>
              </div>
            </div>
          ))}
        </section>

        <label className="flex items-start gap-2 rounded-xl border border-primary/10 bg-gray-bg/40 px-3 py-3 text-sm">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={autoApprove}
            onChange={(e) => setAutoApprove(e.target.checked)}
          />
          <span>
            <span className="font-medium text-primary">Approve immediately</span>
            <span className="mt-0.5 block text-muted">
              Sets status to approved and syncs to Fleetbase when configured. Leave unchecked for
              pending review.
            </span>
          </span>
        </label>
      </form>
    </Drawer>
  );
}
