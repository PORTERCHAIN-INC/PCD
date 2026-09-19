"use client";

import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchants, type MerchantOrgContact } from "@/lib/merchants";
import { Badge, Button, Field, Input, SectionCard } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";

const ROLE_OPTIONS = [
  { id: "accounts_payable", label: "Accounts payable" },
  { id: "operations", label: "Operations" },
  { id: "after_hours", label: "After hours" },
  { id: "shipping", label: "Shipping" },
];

const emptyForm = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  designation: "",
  department: "",
  is_primary: false,
  roles: [] as string[],
};

export default function MerchantContactsPanel({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data, error } = useApiData((t) => merchants.contacts(t, id), [id, version], {
    key: `merchant-contacts-${id}`,
  });
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const refresh = () => setVersion((v) => v + 1);

  function startEdit(contact: MerchantOrgContact) {
    setEditingId(contact.id);
    setForm({
      first_name: contact.first_name,
      last_name: contact.last_name ?? "",
      email: contact.email ?? "",
      phone: contact.phone ?? "",
      designation: contact.designation ?? "",
      department: contact.department ?? "",
      is_primary: contact.is_primary,
      roles: (contact.roles ?? []).filter((role) => ROLE_OPTIONS.some((opt) => opt.id === role)),
    });
    setFormError(null);
  }

  function reset() {
    setEditingId(null);
    setForm(emptyForm);
    setFormError(null);
  }

  async function save() {
    setBusy(true);
    setFormError(null);
    try {
      const token = await getApiToken();
      const body = {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim() || undefined,
        email: form.email.trim() || undefined,
        phone: form.phone.trim() || undefined,
        designation: form.designation.trim() || undefined,
        department: form.department.trim() || undefined,
        is_primary: form.is_primary,
        roles: form.roles,
      };
      if (editingId) await merchants.updateContact(token, id, editingId, body);
      else await merchants.createContact(token, id, body);
      reset();
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not save this contact");
    } finally {
      setBusy(false);
    }
  }

  async function remove(contact: MerchantOrgContact) {
    if (!contact.can_delete) {
      setFormError("Remove this teammate from the Team tab, not Contacts.");
      return;
    }
    if (!window.confirm(`Remove ${contact.first_name} from this company file?`)) return;
    setBusy(true);
    setFormError(null);
    try {
      const token = await getApiToken();
      await merchants.deleteContact(token, id, contact.id);
      if (editingId === contact.id) reset();
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not remove this contact");
    } finally {
      setBusy(false);
    }
  }

  function toggleRole(role: string) {
    setForm((current) => ({
      ...current,
      roles: current.roles.includes(role)
        ? current.roles.filter((item) => item !== role)
        : [...current.roles, role],
    }));
  }

  const rows = data ?? [];

  return (
    <div className="space-y-5">
      <SectionCard title={editingId ? "Edit contact" : "Add contact"}>
        <div className="grid gap-3 p-5 sm:grid-cols-2">
          <Field label="First name">
            <Input
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            />
          </Field>
          <Field label="Last name">
            <Input
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
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
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </Field>
          <Field label="Title">
            <Input
              value={form.designation}
              onChange={(e) => setForm({ ...form, designation: e.target.value })}
            />
          </Field>
          <Field label="Department">
            <Input
              value={form.department}
              onChange={(e) => setForm({ ...form, department: e.target.value })}
            />
          </Field>
          <label className="flex items-center gap-2 text-sm text-primary sm:col-span-2">
            <input
              type="checkbox"
              checked={form.is_primary}
              onChange={(e) => setForm({ ...form, is_primary: e.target.checked })}
            />
            Primary contact
          </label>
          <div className="flex flex-wrap gap-2 sm:col-span-2">
            {ROLE_OPTIONS.map((role) => {
              const on = form.roles.includes(role.id);
              return (
                <button
                  key={role.id}
                  type="button"
                  onClick={() => toggleRole(role.id)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
                    on
                      ? "border-secondary bg-secondary/10 text-secondary"
                      : "border-primary/15 text-muted hover:bg-gray-bg"
                  }`}
                >
                  {role.label}
                </button>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-2 sm:col-span-2">
            <Button onClick={() => void save()} disabled={busy || !form.first_name.trim()}>
              {editingId ? "Save contact" : "Add contact"}
            </Button>
            {editingId ? (
              <Button variant="outline" onClick={reset} disabled={busy}>
                Cancel
              </Button>
            ) : null}
          </div>
          {formError ? <p className="text-sm text-red-600 sm:col-span-2">{formError}</p> : null}
        </div>
      </SectionCard>

      <SectionCard title={`People (${rows.length})`}>
        {error ? <p className="px-5 py-4 text-sm text-red-600">{error}</p> : null}
        <div className="divide-y divide-primary/5">
          {rows.map((contact) => (
            <div
              key={contact.id}
              className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-primary">
                  {contact.first_name} {contact.last_name ?? ""}{" "}
                  {contact.is_primary ? <Badge tone="blue">Primary</Badge> : null}
                  {(contact.source === "team" || contact.roles.includes("portal_team")) && (
                    <Badge tone="amber">Portal team</Badge>
                  )}
                </p>
                <p className="text-xs text-muted">
                  {[contact.designation, contact.email, contact.phone]
                    .filter(Boolean)
                    .join(" · ") || "—"}
                </p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {contact.roles
                    .filter((role) => role !== "portal_team" && !role.startsWith("merchant_"))
                    .map((role) => (
                      <Badge key={role} tone="slate">
                        {titleCase(role.replace(/_/g, " "))}
                      </Badge>
                    ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" onClick={() => startEdit(contact)}>
                  Edit
                </Button>
                <Button
                  variant="danger"
                  disabled={!contact.can_delete || busy}
                  onClick={() => void remove(contact)}
                >
                  Remove
                </Button>
              </div>
            </div>
          ))}
          {rows.length === 0 && !error ? (
            <p className="px-5 py-10 text-center text-sm text-muted">
              No people on this company file yet. Add a contact here or they will appear when a
              teammate is invited.
            </p>
          ) : null}
        </div>
      </SectionCard>
    </div>
  );
}
