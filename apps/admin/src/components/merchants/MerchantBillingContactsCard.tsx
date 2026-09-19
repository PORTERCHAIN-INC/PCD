"use client";

import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchants, type MerchantBillingContact } from "@/lib/merchants";
import { Badge, Button, Field, Input, SectionCard } from "@/components/crm/primitives";

const emptyForm = { name: "", email: "", phone: "" };

export default function MerchantBillingContactsCard({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data, error } = useApiData((t) => merchants.billingContacts(t, id), [id, version], {
    key: `merchant-billing-contacts-${id}`,
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const rows = data ?? [];

  const refresh = () => setVersion((v) => v + 1);

  function reset() {
    setEditingId(null);
    setForm(emptyForm);
    setFormError(null);
  }

  function startEdit(row: MerchantBillingContact) {
    setEditingId(row.id);
    setForm({
      name: row.name,
      email: row.email,
      phone: row.phone ?? "",
    });
    setFormError(null);
  }

  async function save() {
    if (!form.name.trim() || !form.email.trim()) {
      setFormError("Name and email are required for the AP contact.");
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      const token = await getApiToken();
      const body = {
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || undefined,
      };
      if (editingId) {
        await merchants.patchBillingContact(token, id, editingId, body);
      } else {
        await merchants.createBillingContact(token, id, {
          ...body,
          is_primary: rows.length === 0,
        });
      }
      reset();
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not save this billing contact");
    } finally {
      setBusy(false);
    }
  }

  async function setPrimary(contactId: string) {
    setBusy(true);
    setFormError(null);
    try {
      const token = await getApiToken();
      await merchants.patchBillingContact(token, id, contactId, { is_primary: true });
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not set the primary AP contact");
    } finally {
      setBusy(false);
    }
  }

  async function remove(contactId: string) {
    if (!window.confirm("Remove this billing contact?")) return;
    setBusy(true);
    setFormError(null);
    try {
      const token = await getApiToken();
      await merchants.deleteBillingContact(token, id, contactId);
      if (editingId === contactId) reset();
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not remove this billing contact");
    } finally {
      setBusy(false);
    }
  }

  return (
    <SectionCard title="Billing contacts">
      <p className="px-5 pt-4 text-sm text-muted">
        Invoice reminders go to the primary AP contact, and Collections calls their number. Same
        list the merchant sees in Settings.
      </p>
      {error ? <p className="px-5 pt-2 text-sm text-red-600">{error}</p> : null}
      {formError ? <p className="px-5 pt-2 text-sm text-red-600">{formError}</p> : null}
      <div className="divide-y divide-primary/5">
        {rows.map((row) => (
          <div key={row.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
            <div className="text-sm text-primary">
              <p>
                {row.name} · {row.email}{" "}
                {row.is_primary ? <Badge tone="blue">Primary AP</Badge> : null}
              </p>
              <p className="text-xs text-muted">
                {row.phone ? (
                  <a
                    href={`tel:${row.phone.replace(/[^+\d]/g, "")}`}
                    className="text-secondary hover:underline"
                  >
                    {row.phone}
                  </a>
                ) : (
                  "No phone — Collections cannot call this contact"
                )}
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" disabled={busy} onClick={() => startEdit(row)}>
                Edit
              </Button>
              {!row.is_primary ? (
                <Button variant="outline" disabled={busy} onClick={() => void setPrimary(row.id)}>
                  Set primary
                </Button>
              ) : null}
              <Button variant="danger" disabled={busy} onClick={() => void remove(row.id)}>
                Remove
              </Button>
            </div>
          </div>
        ))}
        {rows.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-muted">No AP contacts yet.</p>
        ) : null}
      </div>
      <div className="grid gap-3 border-t border-primary/10 p-5 sm:grid-cols-2">
        <p className="text-sm font-medium text-primary sm:col-span-2">
          {editingId ? "Edit billing contact" : "Add billing contact"}
        </p>
        <Field label="Name">
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Email">
          <Input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </Field>
        <Field label="Phone">
          <Input
            type="tel"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            placeholder="416-555-0100"
          />
        </Field>
        <div className="flex flex-wrap gap-2 sm:col-span-2">
          <Button onClick={() => void save()} disabled={busy}>
            {editingId ? "Save billing contact" : "Add billing contact"}
          </Button>
          {editingId ? (
            <Button variant="outline" disabled={busy} onClick={reset}>
              Cancel
            </Button>
          ) : null}
        </div>
      </div>
    </SectionCard>
  );
}
