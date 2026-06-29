"use client";

import { useMemo, useState } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { crm, type Company, type Contact } from "@/lib/crm";
import { CrmTable } from "@/components/crm/CrmTable";
import { Avatar, Badge, Button, Drawer, Field, Input, Select } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";

const ROLES = [
  "decision_maker",
  "primary_contact",
  "influencer",
  "accounts_payable",
  "warehouse_manager",
  "shipping_manager",
  "operations_manager",
  "purchasing",
  "owner",
];

const blank = (): Partial<Contact> => ({ first_name: "", last_name: "", email: "", roles: [] });

export default function ContactsPage() {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data, error } = useApiData((t) => crm.contacts(t), [version]);
  const { data: companies } = useApiData((t) => crm.companies(t), []);

  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Partial<Contact>>(blank());
  const [busy, setBusy] = useState(false);

  const companyName = useMemo(() => {
    const map = new Map<string, string>();
    (companies ?? []).forEach((c: Company) => map.set(c.id, c.operating_name || c.legal_name));
    return map;
  }, [companies]);

  async function submitCreate() {
    if (!form.first_name) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createContact(token, form);
      setCreating(false);
      setForm(blank());
      setVersion((v) => v + 1);
    } finally {
      setBusy(false);
    }
  }

  function toggleRole(role: string) {
    const roles = new Set(form.roles ?? []);
    if (roles.has(role)) roles.delete(role);
    else roles.add(role);
    setForm({ ...form, roles: [...roles] });
  }

  const columns = useMemo<ColumnDef<Contact, unknown>[]>(
    () => [
      {
        accessorKey: "first_name",
        header: "Name",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <Avatar name={`${row.original.first_name} ${row.original.last_name ?? ""}`} />
            <div>
              <p className="font-semibold text-primary">
                {row.original.first_name} {row.original.last_name}
              </p>
              <p className="text-xs text-muted">{row.original.designation ?? "—"}</p>
            </div>
          </div>
        ),
      },
      {
        accessorKey: "company_id",
        header: "Company",
        cell: ({ getValue }) => companyName.get(String(getValue())) ?? "—",
      },
      { accessorKey: "email", header: "Email", cell: ({ getValue }) => String(getValue() ?? "—") },
      { accessorKey: "phone", header: "Phone", cell: ({ getValue }) => String(getValue() ?? "—") },
      {
        id: "roles",
        header: "Roles",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-1">
            {row.original.roles.slice(0, 3).map((r) => (
              <Badge key={r} tone="slate">
                {titleCase(r)}
              </Badge>
            ))}
            {row.original.roles.length > 3 && (
              <Badge tone="slate">+{row.original.roles.length - 3}</Badge>
            )}
          </div>
        ),
      },
    ],
    [companyName]
  );

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-4">
      <CrmTable
        data={data}
        columns={columns}
        searchPlaceholder="Search contacts…"
        emptyTitle="No contacts yet"
        emptyHint="Add unlimited contacts per merchant company."
        toolbar={
          <Button onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" />
            New Contact
          </Button>
        }
      />

      <Drawer
        open={creating}
        onClose={() => setCreating(false)}
        title="New contact"
        footer={
          <>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button onClick={submitCreate} disabled={busy || !form.first_name}>
              Create contact
            </Button>
          </>
        }
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="First name *">
            <Input
              value={form.first_name ?? ""}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            />
          </Field>
          <Field label="Last name">
            <Input
              value={form.last_name ?? ""}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </Field>
          <Field label="Company" className="col-span-2">
            <Select
              value={form.company_id ?? ""}
              onChange={(e) => setForm({ ...form, company_id: e.target.value })}
            >
              <option value="">— None —</option>
              {(companies ?? []).map((c: Company) => (
                <option key={c.id} value={c.id}>
                  {c.operating_name || c.legal_name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Designation">
            <Input
              value={form.designation ?? ""}
              onChange={(e) => setForm({ ...form, designation: e.target.value })}
            />
          </Field>
          <Field label="Department">
            <Input
              value={form.department ?? ""}
              onChange={(e) => setForm({ ...form, department: e.target.value })}
            />
          </Field>
          <Field label="Email">
            <Input
              value={form.email ?? ""}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </Field>
          <Field label="Phone">
            <Input
              value={form.phone ?? ""}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </Field>
          <Field label="Mobile">
            <Input
              value={form.mobile ?? ""}
              onChange={(e) => setForm({ ...form, mobile: e.target.value })}
            />
          </Field>
          <Field label="LinkedIn">
            <Input
              value={form.linkedin ?? ""}
              onChange={(e) => setForm({ ...form, linkedin: e.target.value })}
            />
          </Field>
          <Field label="Roles" className="col-span-2">
            <div className="flex flex-wrap gap-2">
              {ROLES.map((r) => {
                const on = (form.roles ?? []).includes(r);
                return (
                  <button
                    key={r}
                    type="button"
                    onClick={() => toggleRole(r)}
                    className={
                      "rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset transition-colors " +
                      (on
                        ? "bg-secondary text-white ring-secondary"
                        : "bg-white text-primary/70 ring-primary/15 hover:bg-gray-bg")
                    }
                  >
                    {titleCase(r)}
                  </button>
                );
              })}
            </div>
          </Field>
        </div>
      </Drawer>
    </div>
  );
}
