"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { drivers, DRIVER_DOC_TYPES, type DriverDocumentPayload } from "@/lib/drivers";
import { Button, Field, Input, Select, Textarea } from "@/components/crm/primitives";

export function AddDriverDocumentForm({
  driverId,
  onAdded,
}: {
  driverId: string;
  onAdded: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [docType, setDocType] = useState("driver_license");
  const [label, setLabel] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const [referenceNumber, setReferenceNumber] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [notes, setNotes] = useState("");

  function reset() {
    setDocType("driver_license");
    setLabel("");
    setFileUrl("");
    setReferenceNumber("");
    setExpiresAt("");
    setNotes("");
    setError(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload: DriverDocumentPayload = {
        doc_type: docType,
        label: label.trim() || undefined,
        file_url: fileUrl.trim() || undefined,
        reference_number: referenceNumber.trim() || undefined,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
        notes: notes.trim() || undefined,
      };
      const token = await getApiToken();
      await drivers.addDocument(token, driverId, payload);
      reset();
      setOpen(false);
      onAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add document");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <Button variant="outline" onClick={() => setOpen(true)}>
        <Plus className="h-4 w-4" /> Add document
      </Button>
    );
  }

  return (
    <form
      onSubmit={submit}
      className="space-y-3 rounded-xl border border-primary/10 bg-gray-bg/30 p-4"
    >
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-primary">New document</h4>
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            reset();
            setOpen(false);
          }}
        >
          Cancel
        </Button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Type">
          <Select value={docType} onChange={(e) => setDocType(e.target.value)}>
            {DRIVER_DOC_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Label">
          <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Optional" />
        </Field>
        <Field label="File URL" className="sm:col-span-2">
          <Input
            value={fileUrl}
            onChange={(e) => setFileUrl(e.target.value)}
            placeholder="Link to scanned PDF or image"
          />
        </Field>
        <Field label="Reference / policy number">
          <Input value={referenceNumber} onChange={(e) => setReferenceNumber(e.target.value)} />
        </Field>
        <Field label="Expires">
          <Input type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
        </Field>
        <Field label="Notes" className="sm:col-span-2">
          <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
        </Field>
      </div>
      <Button type="submit" disabled={busy}>
        {busy ? "Saving…" : "Save document"}
      </Button>
    </form>
  );
}
